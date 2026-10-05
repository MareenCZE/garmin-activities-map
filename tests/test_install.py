"""Tests for install.py: config-local.toml editing, finding Python, the venv and the setup questions.

Prompts are answered by replacing ``input`` and ``getpass``; the Garmin login and the
first run are stubbed, so nothing leaves the machine.
"""
import shutil
import tomllib
import types

import pytest
from cryptography.fernet import Fernet

import common
import install


def answer(monkeypatch, *answers, secrets=()):
    """Feed the given answers to input() and the hidden ones to getpass(), in order."""
    answers, secrets = iter(answers), iter(secrets)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr(install.getpass, "getpass", lambda prompt="": next(secrets))


class TestSetTomlValue:
    def test_appends_a_missing_section(self):
        text = install.set_toml_value(install.LOCAL_CONFIG_HEADER, "ftp", "host", "ftp.example.com")
        assert text == install.LOCAL_CONFIG_HEADER + '\n[ftp]\nhost = "ftp.example.com"\n'

    def test_adds_the_key_at_the_end_of_its_section(self):
        text = '[ftp]\nhost = "a"\n\n[mode]\ndownloader = "ON"\n'
        text = install.set_toml_value(text, "ftp", "user", "demo")
        assert text == '[ftp]\nhost = "a"\nuser = "demo"\n\n[mode]\ndownloader = "ON"\n'

    def test_replaces_the_key_and_keeps_comments_and_other_tables(self):
        text = ('# my settings\n[map-tiles] # keys\n# CARTO\ncarto-api-key = "old"\n'
                'tiles = [\n  { tiles="OpenStreetMap", name="OSM" },\n]\n')
        text = install.set_toml_value(text, "map-tiles", "carto-api-key", "new")
        assert text == ('# my settings\n[map-tiles] # keys\n# CARTO\ncarto-api-key = "new"\n'
                        'tiles = [\n  { tiles="OpenStreetMap", name="OSM" },\n]\n')

    def test_does_not_touch_the_same_key_in_another_section(self):
        text = '[a]\nkey = "1"\n[b]\nkey = "2"\n'
        assert install.set_toml_value(text, "b", "key", "3") == '[a]\nkey = "1"\n[b]\nkey = "3"\n'

    def test_section_before_an_array_of_tables(self):
        text = '[mode]\n\n[[presets]]\nname = "x"\n'
        text = install.set_toml_value(text, "mode", "uploader", "OFF")
        assert tomllib.loads(text) == {"mode": {"uploader": "OFF"}, "presets": [{"name": "x"}]}

    def test_apply_settings_escapes_values(self):
        value = 'a "quoted" \\ back\tslash ü'
        text = install.apply_settings("", {("ftp", "pass"): value, ("ftp", "user"): "u"})
        assert tomllib.loads(text) == {"ftp": {"pass": value, "user": "u"}}


class TestFindPython:
    @pytest.fixture
    def old_python(self, monkeypatch):
        monkeypatch.setattr(install, "sys", types.SimpleNamespace(version_info=(3, 9, 0), executable="old"))
        monkeypatch.setattr(install, "IS_WINDOWS", False)

    def test_uses_this_interpreter_when_new_enough(self):
        assert install.find_python() == [install.sys.executable]

    def test_finds_the_newest_suitable_one_on_path(self, old_python, monkeypatch):
        on_path = {"python3.13": (3, 13), "python3.12": (3, 12), "python3": (3, 9)}
        monkeypatch.setattr(install.shutil, "which", lambda name: name if name in on_path else None)
        monkeypatch.setattr(install, "python_version", lambda command: on_path[command[0]])
        assert install.find_python() == ["python3.13"]

    def test_none_when_only_old_ones_exist(self, old_python, monkeypatch):
        monkeypatch.setattr(install.shutil, "which", lambda name: name if name == "python3" else None)
        monkeypatch.setattr(install, "python_version", lambda command: (3, 10))
        assert install.find_python() is None

    def test_set_up_stops_with_a_hint(self, old_python, monkeypatch, capsys):
        monkeypatch.setattr(install.shutil, "which", lambda name: None)
        assert install.set_up_environment("venv") is False
        assert "needs Python 3.12 or newer" in capsys.readouterr().out


class TestEnsureVenv:
    def test_reuses_a_working_venv(self, monkeypatch, tmp_path):
        monkeypatch.setattr(install, "venv_is_usable", lambda venv_dir: True)
        monkeypatch.setattr(install.subprocess, "run", pytest.fail)
        assert install.ensure_venv(["python3"], str(tmp_path))

    def test_recreates_a_broken_venv_when_allowed(self, monkeypatch, tmp_path):
        venv_dir = tmp_path / "venv"
        (venv_dir / "bin").mkdir(parents=True)
        (venv_dir / "bin" / "python").write_text("made on another computer")
        monkeypatch.setattr(install, "venv_is_usable", lambda venv_dir: False)
        answer(monkeypatch, "y")
        calls = []
        monkeypatch.setattr(install.subprocess, "run",
                            lambda command, **kwargs: calls.append(command) or types.SimpleNamespace(returncode=0))
        assert install.ensure_venv(["python3"], str(venv_dir))
        assert not venv_dir.exists()  # the stub did not create it again
        assert calls == [["python3", "-m", "venv", str(venv_dir)]]

    def test_keeps_a_broken_venv_when_declined(self, monkeypatch, tmp_path):
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        answer(monkeypatch, "n")
        assert not install.ensure_venv(["python3"], str(venv_dir))
        assert venv_dir.exists()


@pytest.fixture
def project(config, monkeypatch, tmp_path):
    """A project directory with only config-default.toml; the Garmin login is stubbed to fail."""
    shutil.copy(install.os.path.join(install.PROJECT_ROOT, "config-default.toml"), tmp_path)
    monkeypatch.setattr(install, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(install, "log_in_to_garmin", lambda: False)
    return tmp_path


def read_local(project):
    return tomllib.loads((project / install.LOCAL_CONFIG).read_text())


class TestConfigure:
    def test_without_publishing(self, project, monkeypatch):
        answer(monkeypatch, "carto-test-key", "", "n")
        assert install.configure()
        assert read_local(project) == {"map-tiles": {"carto-api-key": "carto-test-key"}, "mode": {"uploader": "OFF"}}
        assert common.config["mode"]["uploader"] == "OFF"  # the shared config follows the file

    def test_publishing_encrypts_the_password(self, project, monkeypatch):
        answer(monkeypatch, "", "", "y", "ftp.example.com", "demo", "", "/www/map", "", "n",
               secrets=["s3cret"])
        install.configure()
        local = read_local(project)
        key = (project / ".auth" / "ftp.key").read_bytes()
        assert Fernet(key).decrypt(local["ftp"].pop("pass").encode()) == b"s3cret"
        assert local == {
            "mode": {"uploader": "ON"},
            "ftp": {"host": "ftp.example.com", "user": "demo", "protocol": "FTPS",
                    "remote-path": "/www/map", "remote-filename": "index.html"},
        }
        assert "s3cret" not in (project / install.LOCAL_CONFIG).read_text()

    def test_running_again_offers_the_saved_answers(self, project, monkeypatch):
        (project / install.LOCAL_CONFIG).write_text(
            '# mine\n[map-tiles]\nmapy-com-api-key = "mapy-test-key"\n\n'
            '[ftp]\nhost = "ftp.example.com"\nuser = "demo"\npass = "encrypted"\nprotocol = "FTP"\n'
            'remote-path = "/map"\nremote-filename = "map.html"\n')
        # Enter everywhere: keys and password kept, publishing stays on, the rest as saved
        answer(monkeypatch, "", "", "", "", "", "", "", "", "n", secrets=[""])
        install.configure()
        text = (project / install.LOCAL_CONFIG).read_text()
        assert text.startswith("# mine\n")
        local = tomllib.loads(text)
        assert local["map-tiles"] == {"mapy-com-api-key": "mapy-test-key"}
        assert local["ftp"] == {"host": "ftp.example.com", "user": "demo", "pass": "encrypted", "protocol": "FTP",
                                "remote-path": "/map", "remote-filename": "map.html"}
        assert local["mode"] == {"uploader": "ON"}

    def test_invalid_local_config_stops(self, project):
        (project / install.LOCAL_CONFIG).write_text("[ftp\n")
        with pytest.raises(SystemExit, match="not valid TOML"):
            install.configure()


class TestFirstRun:
    @pytest.fixture
    def runs(self, config, monkeypatch):
        """Each tool run adds the next number of activities from ``runs.added``; records the arguments."""
        config["activities"]["max-number-of-activities"] = 3
        state = types.SimpleNamespace(added=[], arguments=[], stored=0)

        def run_tool(arguments):
            state.arguments.append(arguments)
            state.stored += state.added.pop(0)
            return True

        monkeypatch.setattr(install, "run_tool", run_tool)
        monkeypatch.setattr(install, "count_stored_activities", lambda: state.stored)
        return state

    def test_downloads_the_next_batch_while_batches_are_full(self, runs, monkeypatch):
        runs.added = [3, 3, 1]
        answer(monkeypatch, "", "", "")
        assert install.first_run(publish=False)
        assert len(runs.arguments) == 3
        assert runs.arguments[0] == ["--downloader", "ON", "--map-creator", "ON", "--uploader", "OFF",
                                     "--utility-mode", "OFF"]

    def test_stops_when_declined(self, runs, monkeypatch):
        runs.added = [3, 3]
        answer(monkeypatch, "", "n")
        assert install.first_run(publish=True)
        assert len(runs.arguments) == 1
        assert runs.arguments[0][5] == "ON"

    def test_can_be_skipped(self, runs, monkeypatch):
        answer(monkeypatch, "n")
        assert not install.first_run(publish=False)
        assert runs.arguments == []

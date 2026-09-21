"""Tests for the activities-map.py command-line overrides.

The entry point has a hyphen in its filename (can't be `import`ed normally), so
we load it via importlib. Its `if __name__ == "__main__"` guard means loading it
does not run the pipeline.
"""
import importlib.util
import os

import pytest

MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "activities-map.py")


def load_cli():
    spec = importlib.util.spec_from_file_location("activities_map_cli", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cli():
    return load_cli()


class TestParseArgs:
    def test_defaults_are_none(self, cli):
        args = cli.parse_args([])
        assert (args.downloader, args.map_creator, args.uploader,
                args.utility_mode, args.activity_id) == (None, None, None, None, None)

    def test_all_flags_parsed(self, cli):
        args = cli.parse_args(["--downloader", "ON", "--map-creator", "OFF",
                               "--uploader", "ON", "--utility-mode", "RESORT_CSV",
                               "--activity-id", "123"])
        assert args.downloader == "ON"
        assert args.map_creator == "OFF"
        assert args.uploader == "ON"
        assert args.utility_mode == "RESORT_CSV"
        assert args.activity_id == "123"

    def test_invalid_stage_value_exits(self, cli):
        with pytest.raises(SystemExit):
            cli.parse_args(["--downloader", "MAYBE"])

    def test_invalid_utility_mode_exits(self, cli):
        with pytest.raises(SystemExit):
            cli.parse_args(["--utility-mode", "NONSENSE"])


class TestApplyModeOverrides:
    def test_overrides_only_given_values(self, cli, config):
        config["mode"]["downloader"] = "ON"
        config["mode"]["uploader"] = "ON"
        cli.apply_mode_overrides(cli.parse_args(["--downloader", "OFF"]))
        assert config["mode"]["downloader"] == "OFF"  # overridden
        assert config["mode"]["uploader"] == "ON"     # untouched

    def test_no_args_leaves_config_untouched(self, cli, config):
        config["mode"]["downloader"] = "ON"
        config["mode"]["utility-mode"] = "OFF"
        cli.apply_mode_overrides(cli.parse_args([]))
        assert config["mode"]["downloader"] == "ON"
        assert config["mode"]["utility-mode"] == "OFF"

    def test_utility_mode_and_activity_id(self, cli, config):
        cli.apply_mode_overrides(cli.parse_args(
            ["--utility-mode", "REDOWNLOAD", "--activity-id", "999"]))
        assert config["mode"]["utility-mode"] == "REDOWNLOAD"
        assert config["mode"]["activity-id"] == "999"


class TestMain:
    def _patch_stages(self, cli, monkeypatch, calls):
        monkeypatch.setattr(cli.downloader, "download_new_activities",
                            lambda: calls.append("download"))
        monkeypatch.setattr(cli.storage, "load_activities_from_csv",
                            lambda *a, **k: calls.append("load") or [])
        monkeypatch.setattr(cli.mapgenerator, "create_map_with_activities",
                            lambda *a, **k: calls.append("map"))
        monkeypatch.setattr(cli.ftpuploader, "upload_map_with_data_to_ftp_incremental",
                            lambda *a, **k: calls.append("upload"))
        monkeypatch.setattr(cli.storage, "resort_database",
                            lambda: calls.append("resort"))

    def test_all_off_runs_no_stage(self, cli, config, monkeypatch):
        calls = []
        self._patch_stages(cli, monkeypatch, calls)
        cli.main(["--downloader", "OFF", "--map-creator", "OFF",
                  "--uploader", "OFF", "--utility-mode", "OFF"])
        assert calls == []

    def test_downloader_on_invokes_only_download(self, cli, config, monkeypatch):
        calls = []
        self._patch_stages(cli, monkeypatch, calls)
        cli.main(["--downloader", "ON", "--map-creator", "OFF",
                  "--uploader", "OFF", "--utility-mode", "OFF"])
        assert calls == ["download"]

    def test_utility_mode_override_runs_maintenance(self, cli, config, monkeypatch):
        calls = []
        self._patch_stages(cli, monkeypatch, calls)
        cli.main(["--downloader", "OFF", "--map-creator", "OFF",
                  "--uploader", "OFF", "--utility-mode", "RESORT_CSV"])
        assert calls == ["resort"]

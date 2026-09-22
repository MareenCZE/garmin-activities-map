"""Tests for ftpuploader.py: crypto round-trip, upload decisions, config, upload."""
import ftplib
from datetime import datetime

import pytest

import ftpuploader


class TestCrypto:
    def test_encrypt_decrypt_round_trip(self, config):
        config["ftp"] = dict(config.get("ftp", {}))
        config["ftp"]["pass"] = "hunter2"
        # encrypt_password prints the token; encrypt directly here for a round trip
        from cryptography.fernet import Fernet
        token = Fernet(ftpuploader.CRYPTO_KEY).encrypt("hunter2".encode())
        assert ftpuploader.decrypt(token) == "hunter2"

    def test_decrypt_of_freshly_encrypted_value(self):
        from cryptography.fernet import Fernet
        token = Fernet(ftpuploader.CRYPTO_KEY).encrypt("répblové".encode())
        assert ftpuploader.decrypt(token) == "répblové"


class TestShouldUploadFile:
    def test_no_remote_info_uploads(self, tmp_path):
        f = tmp_path / "x.json"
        f.write_text("data")
        assert ftpuploader.should_upload_file(f, None) is True

    def test_manifest_always_uploads_even_if_same_size(self, tmp_path):
        f = tmp_path / "manifest.json"
        f.write_text("12345")
        remote = {"size": len("12345"), "mtime": 0}
        assert ftpuploader.should_upload_file(f, remote) is True

    def test_size_differs_uploads(self, tmp_path):
        f = tmp_path / "cat.json"
        f.write_text("abcdef")
        assert ftpuploader.should_upload_file(f, {"size": 3, "mtime": 0}) is True

    def test_same_size_skips(self, tmp_path):
        f = tmp_path / "cat.json"
        f.write_text("abcdef")
        assert ftpuploader.should_upload_file(f, {"size": 6, "mtime": 0}) is False


class TestFtpConfig:
    def test_create_config_decrypts_password(self):
        from cryptography.fernet import Fernet
        token = Fernet(ftpuploader.CRYPTO_KEY).encrypt("s3cret".encode()).decode()
        cfg = {"ftp": {"host": "h", "user": "u", "pass": token,
                       "remote-path": "/p", "remote-filename": "index.html"}}
        fc = ftpuploader.FtpConfig.create_config(cfg)
        assert fc.host == "h"
        assert fc.user == "u"
        assert fc.password == "s3cret"
        assert fc.remote_path == "/p"
        assert fc.remote_filename == "index.html"


class FakeFtp:
    """Records FTP operations so we can assert on upload behaviour offline."""
    def __init__(self, host):
        self.host = host
        self.stored = []          # names passed to STOR
        self.made_dirs = []
        self.cwd_calls = []
        self.deleted = []         # names passed to DELE
        self.remote_sizes = {}    # filename -> size, drives get_remote_file_info
        self.nlst_files = []      # names returned by NLST in the data dir
        self.mkd_error = None     # if set, mkd() raises it
        self.cwd_errors = {}      # path -> exception cwd() should raise
        self.delete_errors = {}   # filename -> exception delete() should raise
        self.quit_raises = None   # if set, quit() raises it
        self.quit_called = False

    def login(self, user, passwd):
        self.user = user

    def cwd(self, path):
        self.cwd_calls.append(path)
        if path in self.cwd_errors:
            raise self.cwd_errors[path]

    def size(self, filename):
        if filename in self.remote_sizes:
            return self.remote_sizes[filename]
        raise ftplib.error_perm("550 not found")

    def sendcmd(self, cmd):
        return "213 20240101000000"

    def mkd(self, name):
        if self.mkd_error is not None:
            raise self.mkd_error
        self.made_dirs.append(name)

    def storbinary(self, cmd, fp):
        # cmd like "STOR name"
        self.stored.append(cmd.split(" ", 1)[1])

    def retrlines(self, cmd, callback):
        if cmd == "NLST":
            for name in self.nlst_files:
                callback(name)

    def delete(self, filename):
        if filename in self.delete_errors:
            raise self.delete_errors[filename]
        self.deleted.append(filename)

    def quit(self):
        self.quit_called = True
        if self.quit_raises is not None:
            raise self.quit_raises


@pytest.fixture
def ftp_output(tmp_path):
    """Create an output/ tree with an HTML file and JSON data files."""
    out = tmp_path / "output"
    data = out / "data"
    data.mkdir(parents=True)
    html = out / "activities_map.html"
    html.write_text("<html></html>")
    (data / "manifest.json").write_text('{"a":1}')
    (data / "running_activities.json").write_text("[1,2,3]")
    return html


class TestIncrementalUpload:
    def test_uploads_all_when_remote_empty(self, config, monkeypatch, ftp_output):
        from cryptography.fernet import Fernet
        token = Fernet(ftpuploader.CRYPTO_KEY).encrypt("pw".encode()).decode()
        config["ftp"] = {"host": "ftp.example.com", "user": "u", "pass": token,
                         "remote-path": "/", "remote-filename": "index.html"}

        captured = {}

        def fake_ftp(host):
            f = FakeFtp(host)
            captured["ftp"] = f
            return f
        monkeypatch.setattr(ftplib, "FTP", fake_ftp)

        ftpuploader.upload_map_with_data_to_ftp_incremental(str(ftp_output))

        f = captured["ftp"]
        # HTML uploaded under the configured remote filename
        assert "index.html" in f.stored
        # both JSON files uploaded (remote had none)
        assert "manifest.json" in f.stored
        assert "running_activities.json" in f.stored

    def test_skips_json_with_matching_size_but_always_manifest(self, config, monkeypatch, ftp_output):
        from cryptography.fernet import Fernet
        token = Fernet(ftpuploader.CRYPTO_KEY).encrypt("pw".encode()).decode()
        config["ftp"] = {"host": "ftp.example.com", "user": "u", "pass": token,
                         "remote-path": "/", "remote-filename": "index.html"}

        data_dir = ftp_output.parent / "data"
        running_size = (data_dir / "running_activities.json").stat().st_size
        html_size = ftp_output.stat().st_size
        manifest_size = (data_dir / "manifest.json").stat().st_size

        captured = {}

        def fake_ftp(host):
            f = FakeFtp(host)
            # remote already has matching sizes for html, running, manifest
            f.remote_sizes = {
                "index.html": html_size,
                "running_activities.json": running_size,
                "manifest.json": manifest_size,
            }
            captured["ftp"] = f
            return f
        monkeypatch.setattr(ftplib, "FTP", fake_ftp)

        ftpuploader.upload_map_with_data_to_ftp_incremental(str(ftp_output))

        f = captured["ftp"]
        # running json matches remote size -> skipped
        assert "running_activities.json" not in f.stored
        # html matches remote size -> skipped
        assert "index.html" not in f.stored
        # manifest is always uploaded regardless of size
        assert "manifest.json" in f.stored

    def test_skips_entirely_when_no_host(self, config, monkeypatch, ftp_output):
        config["ftp"] = dict(config["ftp"])
        config["ftp"]["host"] = ""

        def boom(host):
            raise AssertionError("should not connect when host is empty")
        monkeypatch.setattr(ftplib, "FTP", boom)

        # should return quietly without attempting a connection
        ftpuploader.upload_map_with_data_to_ftp_incremental(str(ftp_output))


def _valid_ftp_token(password="pw"):
    from cryptography.fernet import Fernet
    return Fernet(ftpuploader.CRYPTO_KEY).encrypt(password.encode()).decode()


def _install_fake_ftp(config, monkeypatch, **fake_attrs):
    """Point config at a working FTP host and patch ftplib.FTP to a FakeFtp.

    Any keyword args are set on the FakeFtp instance before the code uses it.
    Returns a dict whose ``["ftp"]`` key holds the created FakeFtp.
    """
    config["ftp"] = {"host": "ftp.example.com", "user": "u", "pass": _valid_ftp_token(),
                     "remote-path": "/", "remote-filename": "index.html"}
    # Some flows (the "clean" upload) open more than one connection; keep them all.
    captured = {"all": []}

    def fake_ftp(host):
        f = FakeFtp(host)
        for k, v in fake_attrs.items():
            setattr(f, k, v)
        captured["ftp"] = f          # latest
        captured["all"].append(f)
        return f
    monkeypatch.setattr(ftplib, "FTP", fake_ftp)
    return captured


class TestGetRemoteFileInfo:
    def test_returns_size_and_mtime_on_success(self):
        f = FakeFtp("h")
        f.remote_sizes = {"a.json": 42}
        info = ftpuploader.get_remote_file_info(f, "a.json")
        assert info["size"] == 42
        # sendcmd returns "213 20240101000000" -> parsed timestamp
        assert info["mtime"] == datetime.strptime("20240101000000", "%Y%m%d%H%M%S").timestamp()

    def test_returns_none_when_file_missing(self):
        f = FakeFtp("h")  # size() raises error_perm for unknown files
        assert ftpuploader.get_remote_file_info(f, "missing.json") is None


class TestCloseFtp:
    def test_none_is_noop(self):
        ftpuploader.close_ftp(None)  # must not raise

    def test_quits_open_connection(self):
        f = FakeFtp("h")
        ftpuploader.close_ftp(f)
        assert f.quit_called is True

    def test_swallows_quit_errors(self):
        f = FakeFtp("h")
        f.quit_raises = ftplib.error_temp("421 timeout")
        ftpuploader.close_ftp(f)  # must not raise


class TestFullUpload:
    def test_uploads_html_and_all_json(self, config, monkeypatch, ftp_output):
        captured = _install_fake_ftp(config, monkeypatch)
        ftpuploader.upload_map_with_data_to_ftp(str(ftp_output))
        f = captured["ftp"]
        # full upload ignores remote size entirely: everything is stored
        assert "index.html" in f.stored
        assert "manifest.json" in f.stored
        assert "running_activities.json" in f.stored
        assert "data" in f.made_dirs

    def test_existing_data_dir_is_not_fatal(self, config, monkeypatch, ftp_output):
        # mkd('data') raising 550 (already exists) must be swallowed
        captured = _install_fake_ftp(config, monkeypatch,
                                     mkd_error=ftplib.error_perm("550 exists"))
        ftpuploader.upload_map_with_data_to_ftp(str(ftp_output))
        f = captured["ftp"]
        assert "index.html" in f.stored
        assert "running_activities.json" in f.stored

    def test_other_mkd_error_is_reported_not_raised(self, config, monkeypatch, ftp_output):
        # a non-550 error is re-raised inside the try, caught by ftplib.all_errors,
        # logged, and does not propagate
        captured = _install_fake_ftp(config, monkeypatch,
                                     mkd_error=ftplib.error_perm("530 permission denied"))
        ftpuploader.upload_map_with_data_to_ftp(str(ftp_output))
        f = captured["ftp"]
        # html uploaded before mkd; json loop never reached
        assert "index.html" in f.stored
        assert "running_activities.json" not in f.stored

    def test_missing_html_returns_without_connecting(self, config, monkeypatch, tmp_path):
        _install_fake_ftp(config, monkeypatch)
        missing = tmp_path / "nope" / "activities_map.html"
        # no data dir either; function should bail on the missing HTML first
        ftpuploader.upload_map_with_data_to_ftp(str(missing))

    def test_missing_data_dir_returns(self, config, monkeypatch, tmp_path):
        _install_fake_ftp(config, monkeypatch)
        out = tmp_path / "output"
        out.mkdir()
        html = out / "activities_map.html"
        html.write_text("<html></html>")  # exists, but no data/ sibling
        ftpuploader.upload_map_with_data_to_ftp(str(html))

    def test_skips_when_no_host(self, config, monkeypatch, ftp_output):
        config["ftp"] = dict(config["ftp"])
        config["ftp"]["host"] = ""
        monkeypatch.setattr(ftplib, "FTP",
                            lambda h: (_ for _ in ()).throw(AssertionError("no connect")))
        ftpuploader.upload_map_with_data_to_ftp(str(ftp_output))


class TestCleanUpload:
    def test_clean_deletes_json_then_uploads(self, config, monkeypatch, ftp_output):
        captured = _install_fake_ftp(
            config, monkeypatch,
            nlst_files=["old_a.json", "old_b.json", "keep.txt"])
        ftpuploader.upload_map_with_data_to_ftp_clean(str(ftp_output))
        clean_conn, upload_conn = captured["all"]
        # first connection deletes only .json files; non-json is left alone
        assert set(clean_conn.deleted) == {"old_a.json", "old_b.json"}
        # second connection runs a normal full upload
        assert "index.html" in upload_conn.stored
        assert "running_activities.json" in upload_conn.stored

    def test_skips_when_no_host(self, config, monkeypatch, ftp_output):
        config["ftp"] = dict(config["ftp"])
        config["ftp"]["host"] = ""
        monkeypatch.setattr(ftplib, "FTP",
                            lambda h: (_ for _ in ()).throw(AssertionError("no connect")))
        ftpuploader.upload_map_with_data_to_ftp_clean(str(ftp_output))


class TestCleanRemoteDataDirectory:
    def _ftp_config(self):
        return ftpuploader.FtpConfig("h", "u", "pw", "/", "index.html")

    def test_deletes_only_json_and_tolerates_delete_errors(self, monkeypatch):
        f = FakeFtp("h")
        f.nlst_files = ["a.json", "b.json", "notes.txt"]
        f.delete_errors = {"b.json": ftplib.error_perm("550 locked")}
        monkeypatch.setattr(ftplib, "FTP", lambda host: f)
        ftpuploader.clean_remote_data_directory(self._ftp_config())
        assert f.deleted == ["a.json"]  # b.json failed but did not abort

    def test_missing_data_dir_is_ok(self, monkeypatch):
        f = FakeFtp("h")
        f.cwd_errors = {"data": ftplib.error_perm("550 no such dir")}
        monkeypatch.setattr(ftplib, "FTP", lambda host: f)
        # should log and return without raising
        ftpuploader.clean_remote_data_directory(self._ftp_config())
        assert f.deleted == []


class TestEncryptPassword:
    def test_prints_token_that_round_trips(self, config, capsys):
        config["ftp"] = dict(config.get("ftp", {}))
        config["ftp"]["pass"] = "plaintext-secret"
        ftpuploader.encrypt_password()
        token = capsys.readouterr().out.strip()
        assert ftpuploader.decrypt(token.encode()) == "plaintext-secret"

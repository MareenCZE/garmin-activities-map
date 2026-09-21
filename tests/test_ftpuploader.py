"""Tests for ftpuploader.py: crypto round-trip, upload decisions, config, upload."""
import ftplib

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
        self.remote_sizes = {}    # filename -> size, drives get_remote_file_info

    def login(self, user, passwd):
        self.user = user

    def cwd(self, path):
        self.cwd_calls.append(path)

    def size(self, filename):
        if filename in self.remote_sizes:
            return self.remote_sizes[filename]
        raise ftplib.error_perm("550 not found")

    def sendcmd(self, cmd):
        return "213 20240101000000"

    def mkd(self, name):
        self.made_dirs.append(name)

    def storbinary(self, cmd, fp):
        # cmd like "STOR name"
        self.stored.append(cmd.split(" ", 1)[1])

    def quit(self):
        pass


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

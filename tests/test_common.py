"""Tests for common.recursive_update, config loading semantics and the Garmin login."""
import pytest
from garminconnect import GarminConnectAuthenticationError, GarminConnectTooManyRequestsError

import common


class TestRecursiveUpdate:
    def test_overrides_scalar(self):
        base = {"a": 1, "b": 2}
        result = common.recursive_update(base, {"b": 99})
        assert result == {"a": 1, "b": 99}

    def test_adds_new_key(self):
        result = common.recursive_update({"a": 1}, {"c": 3})
        assert result == {"a": 1, "c": 3}

    def test_merges_nested_dicts_preserving_siblings(self):
        base = {"ftp": {"host": "h", "user": "u"}, "mode": {"downloader": "ON"}}
        override = {"ftp": {"user": "override", "pass": "secret"}}
        result = common.recursive_update(base, override)
        # sibling key in nested table is preserved, not clobbered
        assert result["ftp"] == {"host": "h", "user": "override", "pass": "secret"}
        assert result["mode"] == {"downloader": "ON"}

    def test_deeply_nested_merge(self):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"c": 10}}}
        result = common.recursive_update(base, override)
        assert result == {"a": {"b": {"c": 10, "d": 2}}}

    def test_mutates_and_returns_first_arg(self):
        base = {"a": 1}
        result = common.recursive_update(base, {"a": 2})
        assert result is base

    def test_empty_override_is_noop(self):
        base = {"a": 1, "b": {"c": 2}}
        result = common.recursive_update(base, {})
        assert result == {"a": 1, "b": {"c": 2}}


class TestConfigLoaded:
    """The merged config object should expose the documented structure."""

    def test_expected_top_level_sections_present(self):
        for section in ("mode", "ftp", "map-tiles", "activities", "storage", "output"):
            assert section in common.config, f"missing config section: {section}"

    def test_storage_paths_are_strings(self):
        storage_cfg = common.config["storage"]
        for key in ("activities-database", "directory-json", "directory-gpx",
                    "directory-coordinates", "directory-token-store"):
            assert isinstance(storage_cfg[key], str)

    def test_activity_mapping_has_categories(self):
        mapping = common.config["activities"]["mapping"]
        assert isinstance(mapping, list) and len(mapping) > 0
        # first category is the catch-all "Other"
        assert mapping[0]["name"] == "Other"


class FakeGarmin:
    """Stand-in for garminconnect.Garmin: records logins, fails the ones listed in ``errors``."""
    created = []
    errors = []

    def __init__(self, email=None, password=None, is_cn=False, prompt_mfa=None):
        self.email, self.password, self.prompt_mfa = email, password, prompt_mfa
        self.tokenstore = None
        FakeGarmin.created.append(self)

    def login(self, tokenstore=None):
        self.tokenstore = tokenstore
        if FakeGarmin.errors:
            raise FakeGarmin.errors.pop(0)


class TestInitApi:
    """init_api resumes from the token store and falls back to a credential login."""

    @pytest.fixture(autouse=True)
    def fake_garmin(self, config, tmp_path, monkeypatch):
        config["storage"]["directory-token-store"] = str(tmp_path / "auth")
        FakeGarmin.created, FakeGarmin.errors = [], []
        monkeypatch.setattr(common, "Garmin", FakeGarmin)
        monkeypatch.setattr(common, "get_credentials", lambda: ("runner@example.com", "secret"))

    def test_resumes_from_token_store(self, config):
        garmin = common.init_api()
        assert garmin is FakeGarmin.created[0] and len(FakeGarmin.created) == 1
        assert garmin.email is None
        assert garmin.tokenstore == config["storage"]["directory-token-store"]

    def test_falls_back_to_credentials_and_saves_to_token_store(self, config):
        FakeGarmin.errors = [GarminConnectAuthenticationError("Username and password are required")]
        garmin = common.init_api()
        assert len(FakeGarmin.created) == 2 and garmin is FakeGarmin.created[1]
        assert garmin.email == "runner@example.com" and garmin.prompt_mfa is common.get_mfa
        # login(tokenstore) with credentials is what persists the new tokens
        assert garmin.tokenstore == config["storage"]["directory-token-store"]

    def test_failed_credential_login_returns_none(self):
        FakeGarmin.errors = [GarminConnectAuthenticationError("no tokens"),
                             GarminConnectAuthenticationError("bad password")]
        assert common.init_api() is None

    def test_rate_limited_resume_returns_none_without_prompting(self, monkeypatch):
        monkeypatch.setattr(common, "get_credentials", lambda: pytest.fail("must not prompt"))
        FakeGarmin.errors = [GarminConnectTooManyRequestsError("429")]
        assert common.init_api() is None

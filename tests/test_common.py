"""Tests for common.recursive_update and config loading semantics."""
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

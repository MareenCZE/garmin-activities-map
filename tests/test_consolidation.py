"""Tests for the pure helpers in consolidation.py.

consolidation.py is an unmaintained utility kept for reference (it drives bulk
Garmin Connect edits behind an ``init_api()`` login). Only its side-effect-free
helpers are unit-testable without a live Garmin session; the API-driven
functions are intentionally not covered here.

Importing the module must not trigger a login — that is guarded behind
``if __name__ == "__main__"``. These tests would fail at import time if that
guard regressed.
"""
import consolidation


def _sample_activity():
    return {
        "activityId": 12345,
        "activityName": "Morning Run",
        "startTimeGMT": "2024-05-01 05:30:00",
        "activityType": {"typeId": 1, "typeKey": "running", "parentTypeId": 17},
        "distance": 10500.0,      # metres  -> 10.5 km
        "duration": 3660.0,       # seconds -> 61 min
        "averageSpeed": 2.5,      # m/s     -> 9.0 km/h
    }


class TestActivityToString:
    def test_formats_key_fields(self):
        s = consolidation.activity_tostring(_sample_activity())
        assert "12345" in s
        assert "Morning Run" in s
        assert "2024-05-01 05:30:00" in s
        assert "typeId=1" in s
        assert "typeKey=running" in s
        assert "parentTypeId=17" in s

    def test_converts_units(self):
        s = consolidation.activity_tostring(_sample_activity())
        assert "distance=10.5" in s        # metres -> km, 1 decimal
        assert "duration=61.0" in s        # seconds -> minutes
        assert "avgSpeed=9.0" in s         # m/s -> km/h


class TestDisplayJson:
    def test_prints_header_and_pretty_json(self, capsys):
        consolidation.display_json("api.get_activity(1)", {"activityId": 1})
        out = capsys.readouterr().out
        assert "api.get_activity(1)" in out
        assert '"activityId": 1' in out    # indented JSON dump

    def test_prints_non_serializable_as_is(self, capsys):
        marker = object()
        consolidation.display_json("call", marker)
        out = capsys.readouterr().out
        assert repr(marker) in out or str(marker) in out


class TestActivityTypes:
    def test_each_entry_is_id_key_parent_triple(self):
        for name, values in consolidation.ACTIVITY_TYPES.items():
            assert len(values) == 3, name
            type_id, type_key, parent_type_id = values
            assert isinstance(type_id, int)
            assert isinstance(type_key, str) and type_key
            assert isinstance(parent_type_id, int)

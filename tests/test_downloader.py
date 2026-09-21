"""Tests for downloader.py: mapping API responses to Activities, GPX handling."""
import csv

import pytest

import downloader
import storage
from conftest import make_activity


# ---- map_to_object: the two Garmin response shapes ------------------------

TOP_LEVEL = {
    "activityId": 123,
    "startTimeLocal": "2024-05-01 07:30:00",
    "activityType": {"typeKey": "running"},
    "distance": 5321.0,   # metres
    "duration": 1830.0,   # seconds
    "activityName": "Morning Run",
}

# shape returned by api.get_activity() (single-activity endpoint)
SUMMARY_DTO = {
    "activityId": 99,
    "summaryDTO": {"startTimeLocal": "2024-05-01T07:30:00.0",
                   "distance": 1000, "duration": 60},
    "activityTypeDTO": {"typeKey": "cycling"},
    "activityName": "Commute",
}


class TestMapToObject:
    def test_top_level_shape(self, storage_env):
        a = downloader.map_to_object(TOP_LEVEL)
        assert a.activity_id == 123
        assert a.distance == 5.32          # metres -> km, 2dp
        assert a.duration == 30.5          # seconds -> minutes, 1dp
        assert a.date == "2024-05-01"
        assert a.time == "07:30"
        assert a.activity_type == "running"
        assert a.name == "Morning Run"
        assert a.filename == "2024-05-01_123_running"
        assert a.has_gps_data is False

    def test_summary_dto_shape(self, storage_env):
        a = downloader.map_to_object(SUMMARY_DTO)
        assert a.activity_id == 99
        assert a.distance == 1.0
        assert a.duration == 1.0
        assert a.activity_type == "cycling"
        assert a.date == "2024-05-01"

    def test_rounding(self, storage_env):
        activity = dict(TOP_LEVEL, distance=1234.5, duration=3661)
        a = downloader.map_to_object(activity)
        assert a.distance == 1.23
        assert a.duration == 61.0


class TestGetDatetime:
    def test_prefers_top_level_start_time(self):
        dt = downloader.get_datetime_from_activity(
            {"startTimeLocal": "2024-05-01 07:30:00",
             "summaryDTO": {"startTimeLocal": "1999-01-01 00:00:00"}})
        assert dt.year == 2024 and dt.hour == 7 and dt.minute == 30

    def test_falls_back_to_summary_dto(self):
        dt = downloader.get_datetime_from_activity(
            {"summaryDTO": {"startTimeLocal": "2024-05-01T07:30:00"}})
        assert dt.year == 2024 and dt.month == 5


class TestSimplifyCoordinates:
    GPX = ('<?xml version="1.0"?>'
           '<gpx version="1.1" creator="t"><trk><trkseg>'
           '<trkpt lat="48.0000" lon="16.0000"></trkpt>'
           '<trkpt lat="48.0010" lon="16.0010"></trkpt>'  # collinear -> dropped
           '<trkpt lat="48.0020" lon="16.0020"></trkpt>'
           '<trkpt lat="48.0020" lon="16.0100"></trkpt>'
           '</trkseg></trk></gpx>')

    def test_drops_collinear_midpoint(self, config):
        config["activities"]["coords-simplification-factor"] = 0.0001
        coords = downloader.simplify_coordinates(self.GPX)
        # endpoints preserved, near-collinear midpoint removed
        assert coords[0] == [48.0, 16.0]
        assert [48.001, 16.001] not in coords
        assert len(coords) < 4

    def test_empty_track_yields_empty(self, config):
        empty = '<?xml version="1.0"?><gpx version="1.1" creator="t"></gpx>'
        assert downloader.simplify_coordinates(empty) == []


class TestWriteCoordinates:
    def test_writes_header_and_rows(self, storage_env):
        a = make_activity(storage, filename="stem")
        a.coordinates = [[48.1, 16.2], [48.3, 16.4]]
        downloader.write_coordinates(a)

        with open(a.coords_filename, newline="") as f:
            rows = list(csv.reader(f))
        assert rows[0] == ["latitude", "longitude"]
        assert rows[1] == ["48.1", "16.2"]
        assert len(rows) == 3


class TestGetProcessedIds:
    def test_returns_ids(self, storage_env):
        acts = [make_activity(storage, activity_id=1),
                make_activity(storage, activity_id=2)]
        assert downloader.get_processed_activity_ids(acts) == [1, 2]

    def test_empty(self):
        assert downloader.get_processed_activity_ids([]) == []


class FakeApi:
    """Minimal stand-in for the garminconnect.Garmin object."""
    def __init__(self, activities):
        self._activities = activities
        self.requested_range = None

    def get_activities_by_date(self, from_date, to_date, _type, order):
        self.requested_range = (from_date, to_date, order)
        return self._activities


class TestDownloadActivities:
    def test_skips_already_processed_and_appends_new(self, storage_env, monkeypatch):
        # existing DB with activity 1 already processed
        storage.write_database([make_activity(storage, activity_id=1, filename="f1")],
                               storage_env.db_path)

        saved = []
        # avoid any network / file writes for json+gpx; just record the calls
        monkeypatch.setattr(downloader, "save_json_and_gpx",
                            lambda api, activity, api_activity: saved.append(activity.activity_id) or activity)
        # create_appender binds the DB filename as a default arg at import time,
        # so redirect it to the tmp DB for this test
        def tmp_appender(filename=str(storage_env.db_path)):
            return open(filename, mode="a", newline="")
        monkeypatch.setattr(storage, "create_appender", tmp_appender)

        api = FakeApi([
            dict(TOP_LEVEL, activityId=1),   # already processed -> skipped
            dict(TOP_LEVEL, activityId=2),   # new -> saved & appended
        ])

        downloader.download_activities(api, from_date="2024-01-01", to_date="2024-12-31")

        assert saved == [2]  # only the new one was saved
        loaded = storage.load_activities_from_csv(load_coordinates=False)
        assert sorted(a.activity_id for a in loaded) == [1, 2]

    def test_caps_at_max_number_of_activities(self, storage_env, monkeypatch, config):
        config["activities"]["max-number-of-activities"] = 2
        storage.write_database([], storage_env.db_path)

        saved = []
        monkeypatch.setattr(downloader, "save_json_and_gpx",
                            lambda api, activity, api_activity: saved.append(activity.activity_id) or activity)
        monkeypatch.setattr(storage, "create_appender",
                            lambda filename=str(storage_env.db_path): open(filename, "a", newline=""))

        api = FakeApi([dict(TOP_LEVEL, activityId=i) for i in (10, 11, 12, 13)])
        downloader.download_activities(api, from_date="2024-01-01")

        assert saved == [10, 11]  # capped to first 2

    def test_defaults_from_date_to_last_activity(self, storage_env, monkeypatch):
        storage.write_database([
            make_activity(storage, activity_id=1, date="2024-01-01", filename="f1"),
            make_activity(storage, activity_id=2, date="2024-03-15", filename="f2"),
        ], storage_env.db_path)
        monkeypatch.setattr(downloader, "save_json_and_gpx",
                            lambda *a, **k: a[1])
        monkeypatch.setattr(storage, "create_appender",
                            lambda filename=str(storage_env.db_path): open(filename, "a", newline=""))

        api = FakeApi([])
        downloader.download_activities(api)
        assert api.requested_range[0] == "2024-03-15"  # last stored date

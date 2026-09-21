"""Tests for storage.py: the Activity model and the CSV "database"."""
import csv

import pytest

import storage
from conftest import make_activity


def write_coords_file(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["latitude", "longitude"])
        w.writerows(rows)


class TestActivity:
    def test_casts_distance_and_duration_to_float(self, storage_env):
        a = make_activity(storage, distance="12.5", duration="45")
        assert a.distance == 12.5
        assert a.duration == 45.0
        assert isinstance(a.distance, float) and isinstance(a.duration, float)

    def test_derives_file_paths_from_config_dirs(self, storage_env):
        a = make_activity(storage, filename="stem")
        assert a.coords_filename == f"{storage_env.coords_dir}/stem.csv"
        assert a.json_filename == f"{storage_env.json_dir}/stem.json"
        assert a.gpx_filename == f"{storage_env.gpx_dir}/stem.gpx"

    def test_coordinates_start_empty(self, storage_env):
        assert make_activity(storage).coordinates == []

    def test_load_coordinates_reads_file_when_gps_present(self, storage_env):
        a = make_activity(storage, filename="stem", has_gps_data=True)
        write_coords_file(a.coords_filename, [[48.1, 16.2], [48.3, 16.4]])
        a.load_coordinates()
        assert a.coordinates == [[48.1, 16.2], [48.3, 16.4]]

    def test_load_coordinates_noop_without_gps(self, storage_env):
        a = make_activity(storage, filename="stem", has_gps_data=False)
        # even if a stray file exists, no-GPS activities load nothing
        write_coords_file(a.coords_filename, [[1.0, 2.0]])
        a.load_coordinates()
        assert a.coordinates == []

    def test_str_contains_id_and_name(self, storage_env):
        a = make_activity(storage, activity_id=42, name="Ride")
        assert "42" in str(a) and "Ride" in str(a)


class TestReadCoordinates:
    def test_rounds_to_configured_decimal_places(self, storage_env, config):
        config["activities"]["coords-decimal-places"] = 3
        path = storage_env.coords_dir / "c.csv"
        write_coords_file(path, [[48.123456, 16.654321]])
        assert storage.read_coordinates(str(path)) == [[48.123, 16.654]]

    def test_empty_file_yields_empty_list(self, storage_env):
        path = storage_env.coords_dir / "c.csv"
        write_coords_file(path, [])
        assert storage.read_coordinates(str(path)) == []


class TestDatabaseRoundTrip:
    def test_write_then_load_preserves_fields(self, storage_env):
        activities = [
            make_activity(storage, activity_id=1, date="2024-01-01",
                          filename="2024-01-01_1_running", has_gps_data=False),
            make_activity(storage, activity_id=2, date="2024-02-02",
                          activity_type="cycling", name="Bike, with comma",
                          filename="2024-02-02_2_cycling", has_gps_data=True),
        ]
        storage.write_database(activities, storage_env.db_path)

        loaded = storage.load_activities_from_csv(load_coordinates=False)
        assert len(loaded) == 2
        assert [a.activity_id for a in loaded] == [1, 2]
        assert loaded[1].activity_type == "cycling"
        assert loaded[1].name == "Bike, with comma"  # comma survives CSV quoting
        assert loaded[1].has_gps_data is True
        assert loaded[0].has_gps_data is False

    def test_loaded_ids_are_ints(self, storage_env):
        storage.write_database([make_activity(storage, activity_id=15685583510)],
                               storage_env.db_path)
        loaded = storage.load_activities_from_csv(load_coordinates=False)
        assert loaded[0].activity_id == 15685583510
        assert isinstance(loaded[0].activity_id, int)

    def test_has_gps_data_only_true_for_exact_string(self, storage_env):
        # write a raw CSV with a non-"True" value and confirm it maps to False
        with open(storage_env.db_path, "w", newline="") as f:
            w = storage.create_writer(f)
            w.writeheader()
            w.writerow({"date": "2024-01-01", "time": "07:30", "type": "running",
                        "duration": 30.0, "distance": 5.0, "activity_id": 1,
                        "name": "n", "filename": "f", "has_gps_data": "true"})
        loaded = storage.load_activities_from_csv(load_coordinates=False)
        assert loaded[0].has_gps_data is False

    def test_load_reads_coordinates_when_requested(self, storage_env):
        a = make_activity(storage, activity_id=1, filename="stem", has_gps_data=True)
        write_coords_file(a.coords_filename, [[48.0, 16.0]])
        storage.write_database([a], storage_env.db_path)

        loaded = storage.load_activities_from_csv(load_coordinates=True)
        assert loaded[0].coordinates == [[48.0, 16.0]]


class TestResortDatabase:
    def test_sorts_by_date_then_id_and_backs_up(self, storage_env):
        activities = [
            make_activity(storage, activity_id=200, date="2024-03-01", filename="c"),
            make_activity(storage, activity_id=100, date="2024-01-01", filename="a"),
            make_activity(storage, activity_id=50, date="2024-01-01", filename="b"),
        ]
        storage.write_database(activities, storage_env.db_path)

        storage.resort_database()

        loaded = storage.load_activities_from_csv(load_coordinates=False)
        assert [a.activity_id for a in loaded] == [50, 100, 200]
        # a timestamped backup of the DB was created
        backups = list(storage_env.tmp_path.glob("activities_list.csv.*"))
        assert len(backups) == 1


class TestDeleteActivity:
    def test_removes_row_and_files(self, storage_env):
        a = make_activity(storage, activity_id=7, filename="stem", has_gps_data=True)
        write_coords_file(a.coords_filename, [[1.0, 2.0]])
        open(a.gpx_filename, "w").close()
        open(a.json_filename, "w").close()
        storage.write_database([a, make_activity(storage, activity_id=8, filename="other")],
                               storage_env.db_path)

        storage.delete_activity(7)

        loaded = storage.load_activities_from_csv(load_coordinates=False)
        assert [x.activity_id for x in loaded] == [8]
        import os
        assert not os.path.exists(a.coords_filename)
        assert not os.path.exists(a.gpx_filename)
        assert not os.path.exists(a.json_filename)

    def test_missing_id_is_noop(self, storage_env):
        storage.write_database([make_activity(storage, activity_id=1, filename="s")],
                               storage_env.db_path)
        storage.delete_activity(999)
        loaded = storage.load_activities_from_csv(load_coordinates=False)
        assert [x.activity_id for x in loaded] == [1]


class TestUpdateActivity:
    def test_replaces_matching_activity(self, storage_env):
        original = make_activity(storage, activity_id=5, name="Old", filename="2024-01-01_5_running")
        storage.write_database([original], storage_env.db_path)

        updated = make_activity(storage, activity_id=5, name="New", filename="2024-01-01_5_running")
        storage.update_activity(updated)

        loaded = storage.load_activities_from_csv(load_coordinates=False)
        assert len(loaded) == 1
        assert loaded[0].name == "New"

    def test_deletes_old_files_when_date_changes(self, storage_env):
        original = make_activity(storage, activity_id=5, date="2024-01-01",
                                 filename="2024-01-01_5_running", has_gps_data=True)
        open(original.gpx_filename, "w").close()
        open(original.json_filename, "w").close()
        write_coords_file(original.coords_filename, [[1.0, 2.0]])
        storage.write_database([original], storage_env.db_path)

        # same id, different date -> old files (different stem) must be removed
        updated = make_activity(storage, activity_id=5, date="2024-06-06",
                                filename="2024-06-06_5_running")
        storage.update_activity(updated)

        import os
        assert not os.path.exists(original.gpx_filename)
        assert not os.path.exists(original.json_filename)
        assert not os.path.exists(original.coords_filename)

    def test_missing_id_is_noop(self, storage_env):
        storage.write_database([make_activity(storage, activity_id=1, filename="s")],
                               storage_env.db_path)
        storage.update_activity(make_activity(storage, activity_id=999, filename="x"))
        loaded = storage.load_activities_from_csv(load_coordinates=False)
        assert [x.activity_id for x in loaded] == [1]

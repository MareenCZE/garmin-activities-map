"""Tests for mapgenerator.py: category mapping, popups, data files, map build."""
import json

import pytest

import mapgenerator
import storage
from conftest import make_activity


# A deterministic mapping config used across tests (independent of config-local).
SAMPLE_MAPPING = [
    {"name": "Other", "color": "grey", "type_keys": []},
    {"name": "Running", "color": "magenta", "type_keys": ["running", "trail_running"]},
    {"name": "Cycling", "color": "deeppink", "type_keys": ["cycling"]},
]


@pytest.fixture
def mapping_config(config):
    config["activities"]["mapping"] = SAMPLE_MAPPING
    config["activities"]["display-mapping-on-load"] = ["Running"]
    config["activities"]["enable-activity-highlighting"] = True
    return config


class TestTypeMappings:
    def test_builds_mappings_with_show_on_load_flag(self, mapping_config):
        mappings = mapgenerator.get_type_mappings()
        assert [m.name for m in mappings] == ["Other", "Running", "Cycling"]
        by_name = {m.name: m for m in mappings}
        assert by_name["Running"].show_on_load is True
        assert by_name["Cycling"].show_on_load is False
        assert by_name["Running"].color == "magenta"

    def test_raises_when_no_mappings(self, config):
        config["activities"]["mapping"] = []
        config["activities"]["display-mapping-on-load"] = []
        with pytest.raises(ValueError):
            mapgenerator.get_type_mappings()

    def test_get_type_mapping_matches_known_key(self, mapping_config):
        mappings = mapgenerator.get_type_mappings()
        assert mapgenerator.get_type_mapping(mappings, "trail_running").name == "Running"
        assert mapgenerator.get_type_mapping(mappings, "cycling").name == "Cycling"

    def test_unmapped_type_falls_into_first_category(self, mapping_config):
        mappings = mapgenerator.get_type_mappings()
        assert mapgenerator.get_type_mapping(mappings, "kitesurfing").name == "Other"


class TestCalculateMapCenter:
    def test_averages_first_coordinates(self, storage_env):
        a1 = make_activity(storage, filename="a")
        a1.coordinates = [[48.0, 16.0], [48.5, 16.5]]
        a2 = make_activity(storage, filename="b")
        a2.coordinates = [[50.0, 18.0]]
        center = mapgenerator.calculate_map_center([a1, a2])
        assert center == [pytest.approx(49.0), pytest.approx(17.0)]  # only first coords

    def test_empty_activities(self):
        assert mapgenerator.calculate_map_center([]) == [0, 0]

    def test_activities_without_coordinates(self, storage_env):
        a = make_activity(storage)  # coordinates == []
        assert mapgenerator.calculate_map_center([a]) == [0, 0]


class TestResolveMapCenter:
    def test_uses_configured_center_point_when_set(self, storage_env, config):
        config["map-tiles"]["center-point"] = [50.0755, 14.4378]
        a = make_activity(storage, filename="a")
        a.coordinates = [[48.0, 16.0]]  # would otherwise average to here
        assert mapgenerator.resolve_map_center([a]) == [50.0755, 14.4378]

    def test_falls_back_to_calculated_center_when_empty(self, storage_env, config):
        config["map-tiles"]["center-point"] = []
        a = make_activity(storage, filename="a")
        a.coordinates = [[48.0, 16.0]]
        assert mapgenerator.resolve_map_center([a]) == [pytest.approx(48.0), pytest.approx(16.0)]

    def test_missing_key_falls_back_to_calculated(self, storage_env, config):
        config["map-tiles"].pop("center-point", None)
        assert mapgenerator.resolve_map_center([]) == [0, 0]


class TestCreateActivityDataFiles:
    def test_writes_category_files_and_manifest(self, storage_env, mapping_config):
        acts = [
            make_activity(storage, activity_id=1, date="2024-01-01",
                          activity_type="running", filename="a"),
            make_activity(storage, activity_id=2, date="2024-06-06",
                          activity_type="cycling", filename="b"),
            make_activity(storage, activity_id=3, date="2024-03-03",
                          activity_type="running", filename="c"),
        ]
        for a in acts:
            a.coordinates = [[48.0, 16.0]]

        out_dir = storage_env.tmp_path / "output"
        manifest = mapgenerator.create_activity_data_files(acts, str(out_dir))

        data_dir = out_dir / "data"
        # Running has 2 activities, Cycling 1, Other 0
        running = json.loads((data_dir / "running_activities.json").read_text())
        assert len(running) == 2
        cycling = json.loads((data_dir / "cycling_activities.json").read_text())
        assert len(cycling) == 1
        # empty category produces no file
        assert not (data_dir / "other_activities.json").exists()

        # manifest reflects counts and date range
        assert manifest["categories"]["Running"]["activity_count"] == 2
        assert manifest["categories"]["Other"]["activity_count"] == 0
        assert manifest["categories"]["Other"]["data_file"] is None
        assert manifest["date_range"] == {"min_date": "2024-01-01", "max_date": "2024-06-06"}
        assert manifest["config"]["enable_highlighting"] is True

    def test_manifest_file_written_to_disk(self, storage_env, mapping_config):
        acts = [make_activity(storage, activity_id=1, activity_type="running", filename="a")]
        acts[0].coordinates = [[1.0, 2.0]]
        out_dir = storage_env.tmp_path / "output"
        mapgenerator.create_activity_data_files(acts, str(out_dir))
        manifest_on_disk = json.loads((out_dir / "data" / "manifest.json").read_text())
        assert "categories" in manifest_on_disk

    def test_activity_payload_is_minimal_and_correct(self, storage_env, mapping_config):
        a = make_activity(storage, activity_id=7, activity_type="running",
                          name="R", date="2024-01-01", distance=5.0, duration=30, filename="a")
        a.coordinates = [[48.0, 16.0]]
        out_dir = storage_env.tmp_path / "output"
        mapgenerator.create_activity_data_files([a], str(out_dir))
        payload = json.loads((out_dir / "data" / "running_activities.json").read_text())[0]
        assert payload == {
            "coordinates": [[48.0, 16.0]],
            "color": "magenta",
            "date": "2024-01-01",
            "name": "R",
            "activity_type": "running",
            "distance": 5.0,
            "duration": 30.0,
            "activity_id": 7,
        }

    def test_empty_activities_uses_epoch_date_range(self, storage_env, mapping_config):
        out_dir = storage_env.tmp_path / "output"
        manifest = mapgenerator.create_activity_data_files([], str(out_dir))
        assert manifest["date_range"] == {"min_date": "1970-01-01", "max_date": "1970-01-01"}


class TestCartoTiles:
    def test_carto_variants_mapping(self):
        assert mapgenerator.CARTO_TILE_VARIANTS["cartodbpositron"] == "light_all"
        assert mapgenerator.CARTO_TILE_VARIANTS["cartodbdark_matter"] == "dark_all"


class TestBuildTileLayer:
    def test_openstreetmap_builtin(self, config):
        layer = mapgenerator.build_tile_layer("OpenStreetMap", "OSM")
        assert layer is not None
        assert layer.layer_name == "OSM"
        # Folium expands the shorthand into the OSM tile URL
        assert "openstreetmap.org" in layer.tiles

    def test_unknown_source_passed_through_with_attribution(self, config):
        layer = mapgenerator.build_tile_layer("https://tiles/{z}/{x}/{y}.png", "Custom")
        assert layer.tiles == "https://tiles/{z}/{x}/{y}.png"
        assert "OpenStreetMap" in layer.options["attribution"]

    def test_carto_with_key_builds_explicit_url(self, config):
        config["map-tiles"]["carto-api-key"] = "KEY42"
        layer = mapgenerator.build_tile_layer("cartodbdark_matter", "Dark")
        assert "basemaps.cartocdn.com/dark_all/" in layer.tiles
        assert "key=KEY42" in layer.tiles

    def test_carto_without_key_falls_back_to_watermarked_shorthand(self, config):
        config["map-tiles"]["carto-api-key"] = ""
        layer = mapgenerator.build_tile_layer("cartodbpositron", "Light")
        assert layer is not None
        # falls back to Folium's shorthand: CARTO URL but no explicit key param
        assert "key=" not in layer.tiles

    def test_mapy_cz_with_key_builds_url(self, config):
        config["map-tiles"]["mapy-cz-api-key"] = "MKEY"
        layer = mapgenerator.build_tile_layer("mapy.cz-winter", "Winter")
        assert "api.mapy.cz/v1/maptiles/winter/" in layer.tiles
        assert "apikey=MKEY" in layer.tiles

    def test_mapy_cz_without_key_is_skipped(self, config):
        config["map-tiles"]["mapy-cz-api-key"] = ""
        assert mapgenerator.build_tile_layer("mapy.cz-outdoor", "Outdoor") is None

    @pytest.mark.parametrize("tile_key,expected", [
        ("mapy.cz-winter", "winter"),
        ("mapy.cz-outdoor", "outdoor"),
        ("mapy.cz-base", "basic"),
        ("mapy.cz", "basic"),
        ("mapy.cz-somethingelse", "basic"),
    ])
    def test_mapy_cz_variant_resolution(self, tile_key, expected):
        assert mapgenerator._mapy_cz_variant(tile_key) == expected


class TestCreateMapTileSelection:
    def test_skips_keyless_mapy_but_keeps_others(self, config):
        import folium
        config["map-tiles"]["tiles"] = [
            {"tiles": "OpenStreetMap", "name": "OSM"},
            {"tiles": "mapy.cz-winter", "name": "Winter"},  # no key -> skipped
        ]
        config["map-tiles"]["mapy-cz-api-key"] = ""
        config["map-tiles"]["zoom-start"] = 8
        m = mapgenerator.create_map([48.0, 16.0])

        tile_names = [c.layer_name for c in m._children.values()
                      if isinstance(c, folium.TileLayer)]
        assert tile_names == ["OSM"]  # keyless Mapy.cz layer was skipped


class TestCreateMapSmoke:
    def test_create_map_builds_with_osm_tile(self, config):
        config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
        config["map-tiles"]["zoom-start"] = 8
        m = mapgenerator.create_map([48.0, 16.0])
        assert m is not None
        # rendering should not raise
        assert "leaflet" in m.get_root().render().lower()

    def test_create_map_with_carto_key_embeds_key_in_tile_url(self, config):
        config["map-tiles"]["tiles"] = [{"tiles": "cartodbdark_matter", "name": "Dark"}]
        config["map-tiles"]["carto-api-key"] = "SECRETKEY123"
        m = mapgenerator.create_map([48.0, 16.0])
        html = m.get_root().render()
        assert "SECRETKEY123" in html
        assert "dark_all" in html


class TestCreateMapWithActivitiesEndToEnd:
    def test_generates_html_and_data_files(self, storage_env, mapping_config):
        config = mapping_config
        config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
        config["map-tiles"]["zoom-start"] = 8

        a = make_activity(storage, activity_id=1, activity_type="running", filename="a")
        a.coordinates = [[48.0, 16.0], [48.1, 16.1]]

        out_html = storage_env.tmp_path / "output" / "activities_map.html"
        mapgenerator.create_map_with_activities([a], str(out_html))

        assert out_html.exists()
        html = out_html.read_text()
        # data files created alongside
        assert (out_html.parent / "data" / "manifest.json").exists()
        assert (out_html.parent / "data" / "running_activities.json").exists()
        # loader script + slider assets injected
        assert "noUiSlider" in html or "nouislider" in html
        # the map variable was found and script injected (no error early-return)
        assert "L.map" in html

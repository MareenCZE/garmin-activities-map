"""Headless-browser test for presets ([[presets]] in the config).

The bookmark button's panel lists the presets; applying one sets what it has of
the view, selection, date range, activity types, base map and display settings,
and leaves the rest (applyMapPreset in templates/activity_loader_template.html).
The panel also turns the current state into a new [[presets]] entry.

Opt-in: the module skips unless Playwright *and* a Chromium build are installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_presets.py
"""
import functools
import http.server
import socket
import socketserver
import threading

import pytest

pytest.importorskip("playwright.sync_api")  # skip module if Playwright is absent

import mapgenerator
import storage

PRESETS = [
    {"name": "Everything", "center": [0.3, 0.3], "zoom": 13, "selection": [[0.25, 0.25], [0.35, 0.35]],
     "image-zoom": 15, "date-range": "year-2023", "types": ["Cycling"], "tiles": "No map",
     "map-opacity": 50, "line-width": 4, "thin-lines": True, "show-direction": False},
    {"name": "Only 2024", "date-range": ["2024-01-01", "2024-12-31"]},
    {"name": "Far away", "selection": [[0.6, 0.6], [0.7, 0.7]]},
]


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _make_track(activity_id, name, date, coords, activity_type):
    a = storage.Activity(activity_id, 5.0, 42.0, date, "07:30", f"f{activity_id}", True, activity_type, name)
    a.coordinates = coords
    return a


@pytest.fixture
def page(config, tmp_path):
    """A run in 2024 near Null Island and a ride in 2023 around (0.3, 0.3); Running shown."""
    from playwright.sync_api import sync_playwright

    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["mapy-com-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 10
    config["map-tiles"]["center-point"] = [0.0, 0.0]
    config["activities"]["display-mapping-on-load"] = ["Running"]
    config.pop("image-presets", None)
    config["presets"] = PRESETS
    tracks = [
        _make_track(1, "Easy run", "2024-05-01", [[0.0, -0.01], [0.0, 0.01]], "running"),
        _make_track(2, "Short ride", "2023-05-01", [[0.3, 0.28], [0.3, 0.32]], "cycling"),
    ]
    mapgenerator.create_map_with_activities(tracks, str(tmp_path / "activities_map.html"))

    port = _free_port()
    handler = functools.partial(_QuietHandler, directory=str(tmp_path))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as exc:  # browser binary not installed
                pytest.skip(f"Chromium not available: {exc}")
            try:
                pg = browser.new_page()
                pg.route("https://tile.openstreetmap.org/**", lambda route: route.abort())
                pg.goto(f"http://127.0.0.1:{port}/activities_map.html")
                pg.wait_for_function("() => (activityData['Running'] || []).length === 1", timeout=20000)
                yield pg
            finally:
                browser.close()
    finally:
        httpd.shutdown()


def _apply(page, name):
    if page.locator("#presets-dialog").is_hidden():
        page.click(".leaflet-control-presets")
    page.locator("#presets-list .preset-item", has_text=name).click()
    # Applying closes the panel.
    assert page.locator("#presets-dialog").is_hidden()


def _state(page):
    return page.evaluate("""() => ({
        center: [mapInstance.getCenter().lat, mapInstance.getCenter().lng],
        zoom: mapInstance.getZoom(),
        types: shownCategories(),
        dates: currentDateRange,
        datePreset: document.getElementById('date-range-preset').value,
        tiles: baseLayerName(activeBaseLayer()),
        display: Object.assign({}, displaySettings),
        // south, west, north, east
        selection: areaSelectBounds && [areaSelectBounds.getSouth(), areaSelectBounds.getWest(),
                                        areaSelectBounds.getNorth(), areaSelectBounds.getEast()],
    })""")


def test_panel_lists_presets_with_what_they_set(page):
    page.click(".leaflet-control-presets")
    items = page.locator("#presets-list .preset-item")
    assert items.count() == 3
    assert items.nth(1).inner_text().splitlines() == ["Only 2024", "2024-01-01 – 2024-12-31"]
    everything = items.nth(0).inner_text()
    for part in ("view", "selection", "image zoom 15", "2023", "Cycling", "No map", "map 50 %",
                 "lines 4 px", "thin lines", "no direction"):
        assert part in everything


def test_full_preset_sets_everything(page):
    _apply(page, "Everything")
    assert page.locator("#area-selection-dialog").is_visible()
    page.wait_for_function("() => (activityData['Cycling'] || []).length === 1", timeout=10000)
    state = _state(page)
    assert state["center"] == pytest.approx([0.3, 0.3], abs=1e-6) and state["zoom"] == 13
    assert state["types"] == ["Cycling"]
    # Trimmed to the days with data, which start on 2023-05-01.
    assert state["dates"] == {"start": "2023-05-01", "end": "2023-12-31"}
    assert state["datePreset"] == "year-2023"
    assert state["tiles"] == "No map"
    assert state["display"] == {"thinLines": True, "lineWidth": 4, "mapOpacity": 50, "showDirection": False}
    assert state["selection"] == pytest.approx([0.25, 0.25, 0.35, 0.35])
    assert page.evaluate("() => imageExportZoom") == 15
    # The display settings dialog shows the new values.
    page.click(".leaflet-control-display-settings")
    assert page.input_value("#line-width-slider") == "4"
    assert page.inner_text("#map-opacity-value") == "50 %"
    assert page.is_checked("#thin-lines-toggle") and not page.is_checked("#show-direction-toggle")

    # The selection's dialog shows, and lists the ride once its data is loaded.
    page.click(".leaflet-control-display-settings")
    page.locator("#area-selection-dialog").wait_for(state="visible", timeout=10000)
    page.wait_for_function(
        "() => document.getElementById('area-selection-dialog').textContent.includes('Short ride')", timeout=10000)


def test_partial_preset_leaves_the_rest(page):
    before = _state(page)
    _apply(page, "Only 2024")
    after = _state(page)
    # Trimmed to the days with data, which end on 2024-05-01.
    assert after["dates"] == {"start": "2024-01-01", "end": "2024-05-01"}
    assert after["datePreset"] == "custom"
    for key in ("center", "zoom", "types", "tiles", "display", "selection"):
        assert after[key] == before[key], key


def test_selection_out_of_sight_is_brought_into_view(page):
    _apply(page, "Far away")
    assert page.locator("#area-selection-dialog").is_visible()
    assert page.evaluate("() => mapInstance.getBounds().contains(areaSelectBounds)")
    assert _state(page)["selection"] == pytest.approx([0.6, 0.6, 0.7, 0.7])


def test_copy_current_state_as_preset(page):
    page.click(".leaflet-control-presets")
    page.click("#presets-new summary")
    # No selection yet: that part can't be taken.
    assert page.is_disabled("#preset-part-selection")
    page.click("#presets-copy")
    lines = page.locator("#presets-toml").input_value().splitlines()
    assert lines[:2] == ["[[presets]]", 'name = "My preset"']
    assert "center = [0, 0]" in lines and "zoom = 10" in lines
    assert not any(line.startswith("selection") for line in lines)
    assert 'date-range = "all"' in lines
    assert 'types = ["Running"]' in lines
    assert 'tiles = "OSM"' in lines and "map-opacity = 100" in lines
    assert "line-width = 2" in lines and "thin-lines = false" in lines and "show-direction = true" in lines
    page.wait_for_function(
        "() => document.getElementById('presets-status').textContent.includes('config-local.toml')", timeout=10000)

    # Only the ticked parts, and the selection once there is one.
    _apply(page, "Far away")
    page.click(".leaflet-control-presets")
    assert not page.is_disabled("#preset-part-selection")
    for part in ("view", "dates", "types", "map", "lines"):
        page.uncheck(f"#preset-part-{part}")
    page.click("#presets-copy")
    lines = page.locator("#presets-toml").input_value().splitlines()
    assert lines[2] == "selection = [[0.6, 0.6], [0.7, 0.7]]"
    assert all(not line.startswith(("center", "date-range", "types", "tiles", "line-width")) for line in lines)

    # Nothing ticked: nothing to copy.
    page.uncheck("#preset-part-selection")
    assert page.is_disabled("#presets-copy")


def test_panels_take_turns_and_fold_away(page):
    page.click(".leaflet-control-presets")
    page.click(".leaflet-control-image-export")
    assert page.locator("#presets-dialog").is_hidden()
    page.click(".leaflet-control-presets")
    assert page.locator("#image-export-dialog").is_hidden()
    page.click(".leaflet-control-toggle-menu")
    assert page.locator("#presets-dialog").is_hidden()
    assert not page.locator("#presets-bar").is_visible()



@pytest.mark.parametrize("button, dialog", [
    (".leaflet-control-presets", "#presets-dialog"),
    (".leaflet-control-image-export", "#image-export-dialog"),
])
def test_panels_close_on_a_tap_outside_but_not_a_drag(page, button, dialog):
    page.click(button)
    panel = page.locator(dialog)
    assert panel.is_visible()
    # Moving or zooming the map, or working the panel, keeps it open.
    page.mouse.move(300, 450)
    page.mouse.down()
    page.mouse.move(360, 400, steps=5)
    page.mouse.up()
    page.click(".leaflet-control-zoom-out")
    page.locator(dialog).click(position={"x": 20, "y": 20})
    assert panel.is_visible()
    # A tap on the map closes it.
    page.mouse.click(300, 450)
    assert panel.is_hidden()
    # So does one on another control, which still works it.
    page.click(button)
    page.click("#type-filter-button")
    assert panel.is_hidden()
    assert page.locator("#type-filter-menu").is_visible()

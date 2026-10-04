"""Headless-browser test for the remembered map state and the selection dialog's view.

A reload shows the map as it was left: view, background map, activity types,
selection, date preset and display settings (the map-state section of
templates/activity_loader_template.html). "Reset to defaults" in the display
settings forgets them. The selection dialog zooms the map to its rectangle, and
folds away with the other controls.

Opt-in: the module skips unless Playwright *and* a Chromium build are installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_saved_state.py
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

SELECTION = [[-0.004, -0.006], [0.004, 0.006]]


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
    """Runs in 2023 and 2024 and a ride in 2024 near Null Island; Running shown."""
    from playwright.sync_api import sync_playwright

    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"},
                                    {"tiles": "CartoDB.Positron", "name": "Light"}]
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["mapy-com-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 12
    config["map-tiles"]["center-point"] = [0.0, 0.0]
    config["activities"]["display-mapping-on-load"] = ["Running"]
    config.pop("image-presets", None)
    config["presets"] = []
    tracks = [
        _make_track(1, "Old run", "2023-05-01", [[0.0, -0.002], [0.0, 0.002]], "running"),
        _make_track(2, "New run", "2024-05-01", [[0.001, -0.002], [0.001, 0.002]], "running"),
        _make_track(3, "Ride", "2024-07-01", [[0.002, -0.002], [0.002, 0.002]], "cycling"),
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
                pg = browser.new_page(viewport={"width": 1000, "height": 700})
                pg.route("https://**.openstreetmap.org/**", lambda route: route.abort())
                pg.route("https://**.basemaps.cartocdn.com/**", lambda route: route.abort())
                pg.goto(f"http://127.0.0.1:{port}/activities_map.html")
                _wait_loaded(pg, "Running")
                yield pg
            finally:
                browser.close()
    finally:
        httpd.shutdown()


def _wait_loaded(page, category):
    page.wait_for_function(f"""() => typeof mapStateRestored !== 'undefined' && mapStateRestored &&
        (activityData['{category}'] || []).length > 0""", timeout=20000)


def _state(page):
    return page.evaluate("""() => ({
        center: [mapInstance.getCenter().lat, mapInstance.getCenter().lng],
        zoom: mapInstance.getZoom(),
        types: shownCategories(),
        datePreset: document.getElementById('date-range-preset').value,
        tiles: baseLayerName(activeBaseLayer()),
        display: Object.assign({}, displaySettings),
        selection: currentMapState(['selection']).selection,
        selectionMode: areaSelectMode,
    })""")


def _wait_zoomed(page):
    page.wait_for_function("() => !mapInstance._animatingZoom")


def test_reload_shows_the_map_as_it_was_left(page):
    page.evaluate(f"""() => {{
        setBaseLayer('Light');
        setCategoryShown('Cycling', true);
        setCategoryShown('Running', false);
        setDateRange('year-2024');
        setDisplaySettings({{ lineWidth: 4, mapOpacity: 60 }});
        mapInstance.setView([0.001, 0.002], 15.5, {{ animate: false }});
        setAreaSelection(L.latLngBounds({SELECTION}));
    }}""")
    page.locator("input[name='area-sel-mode'][value='full']").check()
    before = _state(page)

    page.reload()  # straight away: the save waiting for the pan to stop is not lost
    _wait_loaded(page, "Cycling")
    after = _state(page)
    assert after["center"] == pytest.approx(before["center"], abs=1e-6)
    for key in ("zoom", "types", "datePreset", "tiles", "display", "selection", "selectionMode"):
        assert after[key] == before[key], key
    assert "1 activity" in page.locator("#area-selection-dialog").inner_text()
    # Only the types shown are downloaded.
    assert page.evaluate("() => 'Running' in activityData") is False


def test_reset_forgets_everything(page):
    default = _state(page)
    page.evaluate(f"""() => {{
        setBaseLayer('Light');
        setCategoryShown('Cycling', true);
        setDateRange('year-2023');
        setDisplaySettings({{ thinLines: true }});
        mapInstance.setView([0.003, 0.003], 14, {{ animate: false }});
        setAreaSelection(L.latLngBounds({SELECTION}));
    }}""")
    page.click(".leaflet-control-display-settings")
    with page.expect_navigation():
        page.click("#reset-map-state")
    _wait_loaded(page, "Running")
    assert _state(page) == default
    assert page.locator("#area-selection-dialog").count() == 0


def test_zoom_to_selection_fills_the_map(page):
    page.evaluate(f"() => setAreaSelection(L.latLngBounds({SELECTION}))")
    page.click("#area-sel-zoom")
    _wait_zoomed(page)
    margins = page.evaluate("""() => {
        const size = mapInstance.getSize();
        const nw = mapInstance.latLngToContainerPoint(areaSelectBounds.getNorthWest());
        const se = mapInstance.latLngToContainerPoint(areaSelectBounds.getSouthEast());
        return { left: nw.x, top: nw.y, right: size.x - se.x, bottom: size.y - se.y };
    }""")
    # Inside the map with the padding around it, and touching it on two sides:
    # not stopped at the whole zoom level below.
    assert min(margins.values()) >= 11
    assert min(margins["left"] + margins["right"], margins["top"] + margins["bottom"]) == pytest.approx(24, abs=2)
    assert page.evaluate("() => mapInstance.options.zoomSnap") == 1


def test_menu_button_folds_the_selection_dialog(page):
    page.evaluate(f"() => setAreaSelection(L.latLngBounds({SELECTION}))")
    dialog = page.locator("#area-selection-dialog")
    assert dialog.is_visible()
    page.click(".leaflet-control-toggle-menu")
    assert dialog.is_hidden()
    # Still folded when the list is redrawn (a filter changed).
    page.evaluate("() => setCategoryShown('Cycling', true)")
    page.wait_for_function("() => (activityData['Cycling'] || []).length === 1")
    page.wait_for_timeout(100)
    assert page.locator("#area-selection-dialog").is_hidden()
    page.click(".leaflet-control-toggle-menu")
    assert page.locator("#area-selection-dialog").is_visible()


@pytest.mark.parametrize("button, close", [
    (".leaflet-control-display-settings", "#display-settings-close"),
    (".leaflet-control-image-export", "#image-export-close"),
    (".leaflet-control-presets", "#presets-close"),
])
def test_panels_hide_the_selection_dialog_while_open(page, button, close):
    page.evaluate(f"() => setAreaSelection(L.latLngBounds({SELECTION}))")
    dialog = page.locator("#area-selection-dialog")
    page.click(button)
    assert dialog.is_hidden()
    page.click(close)
    assert dialog.is_visible()

"""Headless-browser test for comparison mode: two maps side by side.

The page opened with "?compare" shows itself twice, in two iframes. The first map
has all the controls, the second only its date range; everything but the dates is
kept in step, and a selection shows on both with its own summary (the comparison
section of templates/activity_loader_template.html).

Opt-in: the module skips unless Playwright *and* a Chromium build are installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_comparison.py
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
    {"name": "Rides in 2024", "date-range": "year-2024", "types": ["Cycling"],
     "selection": [[-0.02, -0.02], [0.02, 0.02]]},
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
def served(config, tmp_path):
    """A run near Null Island in 2023 and two in 2024, and a ride in 2024; Running shown."""
    from playwright.sync_api import sync_playwright

    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"},
                                    {"tiles": "CartoDB.Positron", "name": "Light"}]
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["mapy-com-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 12
    config["map-tiles"]["center-point"] = [0.0, 0.0]
    config["activities"]["display-mapping-on-load"] = ["Running"]
    config.pop("image-presets", None)
    config["presets"] = PRESETS
    tracks = [
        _make_track(1, "Old run", "2023-05-01", [[0.0, -0.01], [0.0, 0.01]], "running"),
        _make_track(2, "New run", "2024-05-01", [[0.005, -0.01], [0.005, 0.01]], "running"),
        _make_track(3, "Other run", "2024-06-01", [[-0.005, -0.01], [-0.005, 0.01]], "running"),
        _make_track(4, "Ride", "2024-07-01", [[0.01, -0.01], [0.01, 0.01]], "cycling"),
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
                pg = browser.new_page(viewport={"width": 1400, "height": 800})
                pg.route("https://**.openstreetmap.org/**", lambda route: route.abort())
                pg.route("https://**.basemaps.cartocdn.com/**", lambda route: route.abort())
                pg.goto(f"http://127.0.0.1:{port}/activities_map.html")
                _wait_loaded(pg)
                yield pg
            finally:
                browser.close()
    finally:
        httpd.shutdown()


def _wait_loaded(frame):
    frame.wait_for_function("() => (activityData['Running'] || []).length === 3", timeout=20000)


def _compare(page):
    """Open the comparison from the single map; returns its (first, second) map frames."""
    page.click(".leaflet-control-comparison")
    page.wait_for_url("**/activities_map.html?compare")
    page.wait_for_function("() => comparisonPanes.primary && comparisonPanes.secondary", timeout=20000)
    first = page.query_selector("#comparison-primary").content_frame()
    second = page.query_selector("#comparison-secondary").content_frame()
    _wait_loaded(first)
    _wait_loaded(second)
    return first, second


def _state(frame):
    return frame.evaluate("""() => ({
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
        folded: mapControlsFolded,
    })""")


def _same_view(a, b):
    assert a["zoom"] == b["zoom"]
    assert a["center"] == pytest.approx(b["center"], abs=1e-6)


def _summary(frame):
    return frame.locator("#area-selection-dialog").inner_text()


def test_opens_with_the_single_maps_state_and_the_same_dates(served):
    served.evaluate("""() => {
        setDateRange('year-2024');
        setBaseLayer('Light');
        setDisplaySettings({ lineWidth: 3.5 });
        mapInstance.setView([0.001, 0.002], 14, { animate: false });
        setAreaSelection(L.latLngBounds([-0.02, -0.02], [0.02, 0.02]));
    }""")
    before = _state(served)
    first, second = _compare(served)

    for frame in (first, second):
        state = _state(frame)
        _same_view(state, before)
        for key in ("types", "dates", "datePreset", "tiles", "display", "selection"):
            assert state[key] == before[key], key
        # The selection is set before the data arrives; its summary follows the data.
        frame.wait_for_function("""() => {
            const dialog = document.getElementById('area-selection-dialog');
            return dialog && dialog.textContent.includes('2 activities');
        }""", timeout=5000)


def test_second_map_shows_only_its_date_range(served):
    first, second = _compare(served)
    assert first.locator(".leaflet-control-comparison").is_visible()
    assert first.locator("#map-layer-selects").is_visible()
    assert second.locator("#date-range-slider-container").is_visible()
    for selector in ("#map-layer-selects", ".leaflet-top.leaflet-right"):
        assert second.locator(selector).is_hidden(), selector
    # Side by side, the same size: the same centre and zoom show the same area.
    boxes = [served.locator(f"#comparison-{role}").bounding_box() for role in ("primary", "secondary")]
    assert boxes[0]["width"] == boxes[1]["width"] and boxes[0]["height"] == boxes[1]["height"]
    assert boxes[0]["x"] < boxes[1]["x"]


def test_view_follows_both_ways(served):
    first, second = _compare(served)
    first.evaluate("() => mapInstance.setView([0.003, 0.004], 15, { animate: false })")
    _same_view(_state(second), _state(first))
    assert _state(second)["zoom"] == 15

    second.evaluate("() => mapInstance.setView([-0.003, 0.001], 13, { animate: false })")
    _same_view(_state(first), _state(second))
    assert _state(first)["zoom"] == 13

    # Dragging the second map with the mouse moves the first one along.
    box = served.locator("#comparison-secondary").bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.7
    served.mouse.move(x, y)
    served.mouse.down()
    served.mouse.move(x - 120, y - 40, steps=6)
    served.mouse.up()
    second.wait_for_function("() => !mapInstance._panAnim || !mapInstance._panAnim._inProgress")
    assert _state(first)["center"][1] > 0.001 + 1e-4
    _same_view(_state(first), _state(second))


def test_controls_of_the_first_map_set_both(served):
    first, second = _compare(served)
    first.select_option("#tile-layer-select", "Light")
    first.click("#type-filter-button")
    first.locator("#type-filter-menu label", has_text="Cycling").click()
    first.click(".leaflet-control-display-settings")
    first.locator("#thin-lines-toggle").check()
    first.locator("#line-width-slider").fill("4")

    state = _state(second)
    assert state["tiles"] == "Light"
    assert "Cycling" in state["types"]
    assert state["display"]["thinLines"] is True
    assert state["display"]["lineWidth"] == 4
    second.wait_for_function("() => (activityData['Cycling'] || []).length === 1")

    first.click(".leaflet-control-toggle-menu")
    assert _state(second)["folded"] is True
    assert second.locator("#date-range-slider-container").is_hidden()
    first.click(".leaflet-control-toggle-menu")
    assert second.locator("#date-range-slider-container").is_visible()


def test_dates_stay_apart(served):
    first, second = _compare(served)
    second.select_option("#date-range-preset", "year-2023")
    assert _state(second)["datePreset"] == "year-2023"
    assert _state(first)["datePreset"] == "all"
    # The second map's range is not remembered for the single map.
    assert first.evaluate("() => localStorage.getItem(DATE_PRESET_STORAGE_KEY)") in (None, "all")

    # A preset on the first map sets the second one's types and selection, not its dates.
    first.click(".leaflet-control-presets")
    first.locator("#presets-list .preset-item", has_text="Rides in 2024").click()
    first_state, second_state = _state(first), _state(second)
    assert first_state["datePreset"] == "year-2024"
    assert second_state["datePreset"] == "year-2023"
    assert second_state["types"] == ["Cycling"]
    assert second_state["selection"] == first_state["selection"]


def test_selection_shows_on_both_with_its_own_summary(served):
    first, second = _compare(served)
    second.select_option("#date-range-preset", "year-2023")
    first.evaluate("() => setAreaSelection(L.latLngBounds([-0.02, -0.02], [0.02, 0.02]))")

    assert _state(second)["selection"] == _state(first)["selection"]
    assert "3 activities" in _summary(first)
    assert "1 activity" in _summary(second) and "Old run" in _summary(second)
    # The first map has the selection's controls; the second only its summary.
    assert first.locator(".area-select-handle").count() == 8
    assert second.locator(".area-select-handle").count() == 0
    for selector in ("#area-sel-close", "input[name='area-sel-mode']", "#area-sel-save-image"):
        assert first.locator(selector).count() > 0, selector
        assert second.locator(selector).count() == 0, selector

    # Resizing, the mode and closing carry over.
    first.evaluate("""() => {
        const handle = areaSelectHandles.getLayers().find(h => h.ns === 'n' && h.we === null);
        handle.fire('dragstart');
        handle.fire('drag', { latlng: L.latLng(0.003, 0) });
        handle.fire('dragend');
    }""")
    assert _state(second)["selection"] == _state(first)["selection"]
    assert _state(second)["selection"][2] == pytest.approx(0.003)
    first.locator("input[name='area-sel-mode'][value='full']").check()
    assert second.evaluate("() => areaSelectMode") == "full"
    first.click("#area-sel-close")
    assert _state(second)["selection"] is None
    assert second.locator("#area-selection-dialog").count() == 0


def test_closing_returns_to_one_map_as_the_first_one_was(served):
    first, second = _compare(served)
    first.evaluate("""() => {
        setDateRange(['2024-01-01', '2024-05-31']);
        setCategoryShown('Cycling', true);
        mapInstance.setView([0.002, -0.001], 15, { animate: false });
        setAreaSelection(L.latLngBounds([-0.01, -0.01], [0.01, 0.01]));
    }""")
    second.select_option("#date-range-preset", "year-2023")
    before = _state(first)

    first.click(".leaflet-control-comparison")
    served.wait_for_url("**/activities_map.html")
    _wait_loaded(served)
    assert served.locator("#comparison").count() == 0
    after = _state(served)
    _same_view(after, before)
    for key in ("types", "dates", "tiles", "display", "selection"):
        assert after[key] == before[key], key
    assert served.evaluate("() => sessionStorage.getItem(COMPARISON_HANDOFF_KEY)") is None

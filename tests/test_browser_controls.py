"""Headless-browser test for the map's control layout and the tiles/types dropdowns.

The date panel heads the top-left stack, with the tiles select and the activity-types
multiselect under it. The top-right column holds the hamburger, the area-select tool
and the zoom bar; the hamburger folds everything but itself. The dropdowns replace Folium's layer control, which stays on
the map hidden. Covers initializeLayerSelects and the layout in
templates/activity_loader_template.html.

Opt-in: the module skips unless Playwright *and* a Chromium build are installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_controls.py
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


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _make_track(activity_id, activity_type, lat):
    a = storage.Activity(activity_id, 5.0, 42.0, "2024-05-01", "07:30",
                          f"f{activity_id}", True, activity_type, f"Track {activity_id}")
    a.coordinates = [[lat, 0.000], [lat, 0.010]]
    return a


@pytest.fixture
def served_map(config, tmp_path):
    """Two base layers; running tracks shown on load, a cycling track not."""
    config["map-tiles"]["tiles"] = [
        {"tiles": "OpenStreetMap", "name": "OSM"},
        {"tiles": "mapy.com-winter", "name": "Mapy Winter"},
    ]
    config["map-tiles"]["mapy-com-api-key"] = "DUMMYKEY"  # builds the layer; tiles 403, irrelevant
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 14
    config["map-tiles"]["center-point"] = [0.0, 0.005]
    config["activities"]["display-mapping-on-load"] = ["Running"]

    tracks = [
        _make_track(1, "running", 0.000),
        _make_track(2, "running", 0.002),
        _make_track(3, "cycling", 0.004),
    ]
    out_html = tmp_path / "activities_map.html"
    mapgenerator.create_map_with_activities(tracks, str(out_html))

    port = _free_port()
    handler = functools.partial(_QuietHandler, directory=str(tmp_path))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{port}/activities_map.html"
    finally:
        httpd.shutdown()


@pytest.fixture
def page(served_map):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # browser binary not installed
            pytest.skip(f"Chromium not available: {exc}")
        try:
            page = browser.new_page(viewport={"width": 1024, "height": 700})
            page.goto(served_map)
            page.wait_for_function(
                "() => typeof activityData === 'object' && (activityData['Running'] || []).length === 2"
                " && !!document.getElementById('type-filter-button')",
                timeout=20000,
            )
            yield page
        finally:
            browser.close()


def _box(page, selector):
    return page.locator(selector).bounding_box()


def _shown_categories(page):
    return page.evaluate(
        "() => Object.keys(layerGroups).filter(n => mapInstance.hasLayer(layerGroups[n]))")


def test_layout_panels_left_buttons_right(page):
    slider = _box(page, "#date-range-slider-container")
    selects = _box(page, "#map-layer-selects")
    hamburger = _box(page, ".leaflet-control-toggle-menu")
    area = _box(page, "#area-select-bar")
    zoom = _box(page, ".leaflet-control-zoom")

    # Left column: date panel, then the dropdowns under it.
    assert slider["x"] == selects["x"] == 10
    assert slider["y"] + slider["height"] <= selects["y"]

    # Right column, top to bottom: hamburger, area select, a gap, zoom.
    right = page.locator(".leaflet-top.leaflet-right")
    for selector in (".leaflet-control-toggle-menu", "#area-select-bar", ".leaflet-control-zoom"):
        assert right.locator(selector).count() == 1
    assert hamburger["x"] + hamburger["width"] == area["x"] + area["width"] == zoom["x"] + zoom["width"]
    assert hamburger["x"] + hamburger["width"] > 1000
    assert hamburger["y"] + hamburger["height"] < area["y"]
    assert area["y"] + area["height"] < zoom["y"]
    # The date panel ends before the button column.
    assert slider["x"] + slider["width"] <= hamburger["x"]

    # Folium's own layer control is replaced by the dropdowns.
    assert page.locator(".leaflet-control-layers").count() == 1
    assert not page.locator(".leaflet-control-layers").is_visible()


FOLDED = ("#date-range-slider-container", "#map-layer-selects", "#area-select-bar",
          ".leaflet-control-zoom")


def test_hamburger_folds_everything_but_itself(page):
    page.click(".leaflet-control-toggle-menu")
    for selector in FOLDED:
        assert not page.locator(selector).is_visible()
    assert page.locator(".leaflet-control-toggle-menu").is_visible()

    page.click(".leaflet-control-toggle-menu")
    for selector in FOLDED:
        assert page.locator(selector).is_visible()


def test_bar_buttons_are_not_underlined_on_hover(page):
    page.hover(".leaflet-control-zoom-in")
    assert page.eval_on_selector(
        ".leaflet-control-zoom-in", "el => getComputedStyle(el).textDecorationLine") == "none"


def test_tile_select_switches_base_layer(page):
    assert page.locator("#tile-layer-select option").all_inner_texts() == ["OSM", "Mapy Winter"]
    assert page.input_value("#tile-layer-select") == "OSM"

    page.select_option("#tile-layer-select", label="Mapy Winter")
    active = page.evaluate(
        "() => Object.keys(baseLayers).filter(n => mapInstance.hasLayer(baseLayers[n]))")
    assert active == ["Mapy Winter"]


def test_types_multiselect_toggles_categories(page):
    button = page.locator("#type-filter-button")
    menu = page.locator("#type-filter-menu")
    assert button.inner_text().startswith("Running")
    assert not menu.is_visible()

    button.click()
    assert menu.is_visible()
    assert menu.locator("label", has_text="Running").locator("input").is_checked()

    # Turning on a category loads its data lazily and updates the summary.
    menu.locator("label", has_text="Cycling").locator("input").check()
    page.wait_for_function("() => (activityData['Cycling'] || []).length === 1", timeout=5000)
    assert sorted(_shown_categories(page)) == ["Cycling", "Running"]
    assert button.inner_text().startswith("Running, Cycling")

    menu.get_by_role("button", name="None").click()
    assert _shown_categories(page) == []
    assert button.inner_text().startswith("No types")

    menu.get_by_role("button", name="All").click()
    assert len(_shown_categories(page)) == page.evaluate("() => Object.keys(layerGroups).length")
    assert button.inner_text().startswith("All types")

    # A press on the map closes the menu.
    page.mouse.click(600, 600)
    assert not menu.is_visible()


def test_single_base_layer_hides_tile_select(config, tmp_path):
    from playwright.sync_api import sync_playwright

    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
    config["activities"]["display-mapping-on-load"] = ["Running"]
    out_html = tmp_path / "activities_map.html"
    mapgenerator.create_map_with_activities([_make_track(1, "running", 0.0)], str(out_html))

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
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{port}/activities_map.html")
                page.wait_for_selector("#type-filter-button", timeout=20000)
                assert not page.locator("#tile-layer-select").is_visible()
            finally:
                browser.close()
    finally:
        httpd.shutdown()

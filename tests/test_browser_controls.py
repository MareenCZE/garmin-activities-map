"""Headless-browser test for the map's control layout and the tiles/types dropdowns.

The date panel heads the top-left stack, with the tiles select and the activity-types
multiselect under it. The top-right column holds the hamburger, the area-select tool,
the save-image camera, the display-settings gear and the zoom bar; the hamburger folds
everything but itself.
The dropdowns replace Folium's layer control, which stays on the map hidden. Covers
initializeLayerSelects, initializeDisplaySettings and the layout in
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
    camera = _box(page, "#image-export-bar")
    settings = _box(page, "#display-settings-bar")
    zoom = _box(page, ".leaflet-control-zoom")

    # Left column: date panel, then the dropdowns under it.
    assert slider["x"] == selects["x"] == 10
    assert slider["y"] + slider["height"] <= selects["y"]

    # Right column, top to bottom: hamburger, area select, save image, settings, a gap, zoom.
    right = page.locator(".leaflet-top.leaflet-right")
    for selector in (".leaflet-control-toggle-menu", "#area-select-bar", "#image-export-bar",
                     "#display-settings-bar", ".leaflet-control-zoom"):
        assert right.locator(selector).count() == 1
    assert (hamburger["x"] + hamburger["width"] == area["x"] + area["width"]
            == camera["x"] + camera["width"] == settings["x"] + settings["width"]
            == zoom["x"] + zoom["width"])
    assert hamburger["x"] + hamburger["width"] > 1000
    assert hamburger["y"] + hamburger["height"] < area["y"]
    assert area["y"] + area["height"] < camera["y"]
    assert camera["y"] + camera["height"] < settings["y"]
    assert settings["y"] + settings["height"] < zoom["y"]
    # The date panel ends before the button column.
    assert slider["x"] + slider["width"] <= hamburger["x"]

    # Folium's own layer control is replaced by the dropdowns.
    assert page.locator(".leaflet-control-layers").count() == 1
    assert not page.locator(".leaflet-control-layers").is_visible()


FOLDED = ("#date-range-slider-container", "#map-layer-selects", "#area-select-bar",
          "#image-export-bar", "#display-settings-bar", ".leaflet-control-zoom")


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


def _track_styles(page):
    return page.evaluate(
        "() => layerGroups['Running'].getLayers()"
        ".map(l => [l.options.weight, l.options.opacity]).sort()")


def test_settings_gear_opens_and_closes_dialog(page):
    dialog = page.locator("#display-settings-dialog")
    assert not dialog.is_visible()

    page.click(".leaflet-control-display-settings")
    assert dialog.is_visible()
    # Level with the gear, left of the button column.
    gear = _box(page, ".leaflet-control-display-settings")
    box = _box(page, "#display-settings-dialog")
    assert box["y"] == gear["y"]
    assert box["x"] + box["width"] <= gear["x"]
    # It stays open while the map is used.
    page.mouse.click(400, 500)
    assert dialog.is_visible()

    page.click("#display-settings-close")
    assert not dialog.is_visible()
    page.click(".leaflet-control-display-settings")
    page.keyboard.press("Escape")
    assert not dialog.is_visible()

    # Folding the controls closes it too.
    page.click(".leaflet-control-display-settings")
    page.click(".leaflet-control-toggle-menu")
    assert not dialog.is_visible()


def test_thin_lines_restyle_tracks_and_are_remembered(page):
    assert _track_styles(page) == [[2, 0.8], [2, 0.8]]

    page.click(".leaflet-control-display-settings")
    page.check("#thin-lines-toggle")
    assert _track_styles(page) == [[1.5, 0.35], [1.5, 0.35]]

    # A track's hover highlight falls back to the thin style.
    page.evaluate("() => { const l = layerGroups['Running'].getLayers()[0];"
                  " l.fire('mouseover'); l.fire('mouseout'); }")
    assert _track_styles(page) == [[1.5, 0.35], [1.5, 0.35]]

    # Kept across a reload, and applied to the tracks drawn on load.
    page.reload()
    page.wait_for_function("() => (activityData['Running'] || []).length === 2", timeout=20000)
    assert _track_styles(page) == [[1.5, 0.35], [1.5, 0.35]]
    page.click(".leaflet-control-display-settings")
    assert page.is_checked("#thin-lines-toggle")

    page.uncheck("#thin-lines-toggle")
    assert _track_styles(page) == [[2, 0.8], [2, 0.8]]


def test_line_width_slider_sets_width_and_combines_with_thin_lines(page):
    page.click(".leaflet-control-display-settings")
    assert page.input_value("#line-width-slider") == "2"
    assert page.inner_text("#line-width-value") == "2 px"

    page.fill("#line-width-slider", "4")
    assert _track_styles(page) == [[4, 0.8], [4, 0.8]]
    assert page.inner_text("#line-width-value") == "4 px"

    # Thin lines take a share of the chosen width.
    page.check("#thin-lines-toggle")
    assert _track_styles(page) == [[3, 0.35], [3, 0.35]]

    page.reload()
    page.wait_for_function("() => (activityData['Running'] || []).length === 2", timeout=20000)
    assert _track_styles(page) == [[3, 0.35], [3, 0.35]]
    page.click(".leaflet-control-display-settings")
    assert page.input_value("#line-width-slider") == "4"


def test_out_of_range_saved_settings_are_clamped(page):
    page.evaluate("() => localStorage.setItem('activitiesMap.displaySettings',"
                  " JSON.stringify({lineWidth: 40, mapOpacity: 1}))")
    page.reload()
    page.wait_for_function("() => (activityData['Running'] || []).length === 2", timeout=20000)
    assert _track_styles(page) == [[5, 0.8], [5, 0.8]]
    assert _tile_pane_opacity(page) == "0.2"


def _tile_pane_opacity(page):
    return page.evaluate("() => mapInstance.getPane('tilePane').style.opacity")


def test_map_opacity_slider_fades_base_map_and_is_remembered(page):
    assert _tile_pane_opacity(page) == ""
    page.click(".leaflet-control-display-settings")
    assert page.input_value("#map-opacity-slider") == "100"

    page.fill("#map-opacity-slider", "40")
    assert _tile_pane_opacity(page) == "0.4"
    assert page.inner_text("#map-opacity-value") == "40 %"
    # The tracks themselves are not faded.
    assert _track_styles(page) == [[2, 0.8], [2, 0.8]]

    page.reload()
    page.wait_for_function("() => !!document.getElementById('display-settings-dialog')", timeout=20000)
    assert _tile_pane_opacity(page) == "0.4"

    page.click(".leaflet-control-display-settings")
    page.fill("#map-opacity-slider", "100")
    assert _tile_pane_opacity(page) == ""


def test_corrupt_saved_settings_fall_back_to_defaults(page):
    page.evaluate("() => localStorage.setItem('activitiesMap.displaySettings', '{not json')")
    page.reload()
    page.wait_for_function("() => (activityData['Running'] || []).length === 2", timeout=20000)
    assert _track_styles(page) == [[2, 0.8], [2, 0.8]]
    assert _tile_pane_opacity(page) == ""


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

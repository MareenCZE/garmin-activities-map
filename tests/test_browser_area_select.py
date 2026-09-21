"""Headless-browser test for the client-side "select area" tool.

Like test_browser_mapy.py, this covers behaviour that pure-Python tests can't:
the JavaScript in templates/activity_loader_template.html that lets the user drag
a rectangle on the map and lists + summarizes the activities inside it, honouring
the "partially inside" / "fully inside" toggle.

It builds a real map with two known tracks, serves it, drives it in headless
Chromium, draws a rectangle with a real mouse drag, and checks the dialog.

Opt-in: the module skips unless Playwright *and* a Chromium build are installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_area_select.py
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


def _make_track(activity_id, name, coords, date="2024-05-01"):
    a = storage.Activity(activity_id, 5.0, 42.0, date, "07:30",
                          f"f{activity_id}", True, "running", name)
    a.coordinates = coords
    return a


@pytest.fixture
def served_map(config, tmp_path):
    """Build a map with two running tracks near [50, 14] and serve it.

    - "Alpha" sits entirely inside a small box around [50.00, 14.00].
    - "Bravo" starts inside that box but runs far outside it, so it is only ever
      *partially* inside.
    """
    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["mapy-com-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 12
    config["map-tiles"]["center-point"] = [50.00, 14.00]
    config["activities"]["display-mapping-on-load"] = ["Running"]

    # Distinct dates so the newest-first display order (Bravo, Alpha) differs from
    # the collection order (Alpha, Bravo) — the case that exposed the row/highlight
    # index mismatch bug.
    alpha = _make_track(1, "Alpha", [[50.000, 14.000], [50.005, 14.005]], date="2024-05-01")
    bravo = _make_track(2, "Bravo", [[50.000, 14.000], [50.200, 14.300]], date="2024-06-01")

    out_html = tmp_path / "activities_map.html"
    mapgenerator.create_map_with_activities([alpha, bravo], str(out_html))

    port = _free_port()
    handler = functools.partial(_QuietHandler, directory=str(tmp_path))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{port}/activities_map.html"
    finally:
        httpd.shutdown()


def _launch(p):
    try:
        return p.chromium.launch()
    except Exception as exc:  # browser binary not installed
        pytest.skip(f"Chromium not available: {exc}")


def _wait_loaded(page):
    """Wait for the loader to wire up controls and load the Running tracks."""
    page.wait_for_selector(".leaflet-control-area-select", timeout=20000)
    page.wait_for_function(
        "() => typeof activityData === 'object' && (activityData['Running'] || []).length === 2",
        timeout=20000,
    )


def _drag_box_around_origin(page):
    """Drag a rectangle covering [49.99..50.01, 13.99..14.01] with a real mouse."""
    corners = page.evaluate(
        """() => {
        const rect = mapInstance.getContainer().getBoundingClientRect();
        const nw = mapInstance.latLngToContainerPoint([50.01, 13.99]);
        const se = mapInstance.latLngToContainerPoint([49.99, 14.01]);
        return {x1: rect.left + nw.x, y1: rect.top + nw.y,
                x2: rect.left + se.x, y2: rect.top + se.y};
    }"""
    )
    page.click(".leaflet-control-area-select")  # arm the tool
    page.mouse.move(corners["x1"], corners["y1"])
    page.mouse.down()
    page.mouse.move(corners["x2"], corners["y2"], steps=8)
    page.mouse.up()
    page.wait_for_selector("#area-selection-dialog", timeout=10000)


def test_rectangle_selects_and_summarizes_activities(served_map):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page = browser.new_page()
            page.goto(served_map)
            _wait_loaded(page)
            _drag_box_around_origin(page)

            dialog = page.locator("#area-selection-dialog")

            # Partially inside (default): both Alpha and Bravo qualify.
            assert dialog.locator(".area-sel-row").count() == 2
            header = dialog.locator("div[style*='font-weight:bold']").first.inner_text()
            assert "2 activities" in header
            # Summary carries distance + duration totals (2 x 5km, 2 x 42min).
            assert "10.0 km" in header
            assert "1h 24min" in header
            # Each row exposes a Garmin Connect link.
            assert dialog.locator(".area-sel-row a[href*='connect.garmin.com']").count() == 2

            # Switch to "fully inside": only Alpha stays.
            dialog.locator("input[value='full']").check()
            page.wait_for_function(
                "() => {const d=document.getElementById('area-selection-dialog');"
                "return d && d.querySelectorAll('.area-sel-row').length === 1;}",
                timeout=10000,
            )
            assert "1 activity" in dialog.locator("div[style*='font-weight:bold']").first.inner_text()

            # Closing the dialog removes it and clears the rectangle.
            dialog.locator("#area-sel-close").click()
            assert page.locator("#area-selection-dialog").count() == 0
        finally:
            browser.close()


def test_respects_type_filter(served_map):
    """Deselecting the Running layer should leave nothing to select."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page = browser.new_page()
            page.goto(served_map)
            _wait_loaded(page)

            # Toggle the Running overlay off via the layer control.
            page.get_by_text("Running", exact=True).click()
            page.wait_for_function(
                "() => Object.values(layerGroups).every(l => !mapInstance.hasLayer(l))",
                timeout=10000,
            )

            _drag_box_around_origin(page)
            dialog = page.locator("#area-selection-dialog")
            assert dialog.locator(".area-sel-row").count() == 0
            assert "0 activities" in dialog.locator("div[style*='font-weight:bold']").first.inner_text()
        finally:
            browser.close()


def _highlighted_track_names(page):
    """Names of the Running polylines currently drawn with the highlight colour."""
    return page.evaluate(
        """() => {
        const names = [];
        (layerGroups['Running'] || {eachLayer: () => {}}).eachLayer(pl => {
            if (pl.options && pl.options.color === '#00FF00') names.push(pl.activityData.name);
        });
        return names;
    }"""
    )


def test_row_hover_highlights_matching_track(served_map):
    """Hovering a row must highlight the track shown in that row (regression)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page = browser.new_page()
            page.goto(served_map)
            _wait_loaded(page)
            _drag_box_around_origin(page)

            rows = page.locator("#area-selection-dialog .area-sel-row")
            assert rows.count() == 2

            for i in range(2):
                shown = rows.nth(i).locator("span[title]").get_attribute("title")
                rows.nth(i).hover()
                page.wait_for_function(
                    "(name) => {const hi=[];(layerGroups['Running']||{eachLayer:()=>{}})"
                    ".eachLayer(pl=>{if(pl.options&&pl.options.color==='#00FF00')hi.push(pl.activityData.name);});"
                    "return hi.length===1 && hi[0]===name;}",
                    arg=shown,
                    timeout=5000,
                )
                assert _highlighted_track_names(page) == [shown]
        finally:
            browser.close()


def test_button_in_zoom_bar_and_folds_with_hamburger(served_map):
    """The tool sits in the zoom toolbar and hides when the hamburger folds controls."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page = browser.new_page()
            page.goto(served_map)
            _wait_loaded(page)

            # Button is a child of the zoom control (next to +/-).
            assert page.locator(".leaflet-control-zoom .leaflet-control-area-select").count() == 1
            assert page.locator(".leaflet-control-area-select").is_visible()

            # Hamburger folds the zoom bar away -> the tool goes with it.
            page.locator(".leaflet-control-toggle-menu").click()
            page.wait_for_function(
                "() => getComputedStyle(document.querySelector('.leaflet-control-zoom')).display === 'none'",
                timeout=5000,
            )
            assert not page.locator(".leaflet-control-area-select").is_visible()
        finally:
            browser.close()


def test_tool_absent_when_disabled(config, tmp_path):
    """With enable-area-selection = false the toolbar button is not added."""
    from playwright.sync_api import sync_playwright

    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["mapy-com-api-key"] = ""
    config["map-tiles"]["center-point"] = [50.0, 14.0]
    config["activities"]["display-mapping-on-load"] = ["Running"]
    config["activities"]["enable-area-selection"] = False

    out_html = tmp_path / "activities_map.html"
    mapgenerator.create_map_with_activities(
        [_make_track(1, "Alpha", [[50.0, 14.0], [50.005, 14.005]])], str(out_html))

    port = _free_port()
    handler = functools.partial(_QuietHandler, directory=str(tmp_path))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = _launch(p)
            try:
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{port}/activities_map.html")
                page.wait_for_selector(".leaflet-control-layers", timeout=20000)
                page.wait_for_function(
                    "() => typeof mapInstance !== 'undefined' && mapInstance !== null",
                    timeout=20000,
                )
                # Give the loader a beat to run its init chain, then assert absence.
                page.wait_for_timeout(500)
                assert page.locator(".leaflet-control-area-select").count() == 0
            finally:
                browser.close()
    finally:
        httpd.shutdown()

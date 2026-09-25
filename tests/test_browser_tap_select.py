"""Headless-browser test for the client-side tap picker.

A click/tap on the map picks the visible activities whose track passes within a
few pixels of it (wider for touch than for a mouse), so a near miss on the thin
line still hits. One match opens its popup; several overlapping tracks are
listed in the selection dialog. Covers onMapTap / computeTapSelection in
templates/activity_loader_template.html.

Opt-in: the module skips unless Playwright *and* a Chromium build are installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_tap_select.py
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


def _make_track(activity_id, name, coords, date):
    a = storage.Activity(activity_id, 5.0, 42.0, date, "07:30",
                          f"f{activity_id}", True, "running", name)
    a.coordinates = coords
    return a


# Horizontal tracks near Null Island: "Solo" on its own along lat 0.01, and two
# tracks sharing the stretch along lat -0.01 ("Twin A" stops at lng 0.01,
# "Twin B" carries on to lng 0.02).
SOLO_LAT = 0.010
TWIN_LAT = -0.010


@pytest.fixture
def served_map(config, tmp_path):
    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["mapy-com-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 14
    config["map-tiles"]["center-point"] = [0.0, 0.005]
    config["activities"]["display-mapping-on-load"] = ["Running"]

    tracks = [
        _make_track(1, "Solo", [[SOLO_LAT, 0.000], [SOLO_LAT, 0.010]], "2024-05-01"),
        _make_track(2, "Twin A", [[TWIN_LAT, 0.000], [TWIN_LAT, 0.010]], "2024-05-02"),
        _make_track(3, "Twin B", [[TWIN_LAT, 0.000], [TWIN_LAT, 0.020]], "2024-06-01"),
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
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:  # browser binary not installed
            pytest.skip(f"Chromium not available: {exc}")
        try:
            yield b
        finally:
            b.close()


def _open(browser, url, touch):
    context = browser.new_context(has_touch=touch, is_mobile=touch)
    page = context.new_page()
    page.goto(url)
    page.wait_for_function(
        "() => typeof activityData === 'object' && (activityData['Running'] || []).length === 3",
        timeout=20000,
    )
    # initializeTapSelection runs right after the data loads; wait for its listener.
    page.wait_for_function(
        "() => mapInstance.listens('click') && mapInstance._events.click"
        ".some(h => h.fn === onMapTap)",
        timeout=10000,
    )
    return page


def _page_point(page, lat, lng, dy=0):
    """Page coordinates of [lat, lng], shifted dy pixels down."""
    return page.evaluate(
        """([lat, lng, dy]) => {
        const rect = mapInstance.getContainer().getBoundingClientRect();
        const p = mapInstance.latLngToContainerPoint([lat, lng]);
        return {x: rect.left + p.x, y: rect.top + p.y + dy};
    }""",
        [lat, lng, dy],
    )


def _popup_text(page):
    popup = page.locator(".leaflet-popup-content")
    popup.wait_for(timeout=5000)
    return popup.inner_text()


def test_touch_near_miss_opens_the_single_match(served_map, browser):
    page = _open(browser, served_map, touch=True)
    pt = _page_point(page, SOLO_LAT, 0.005, dy=14)  # well off the 2 px line
    page.touchscreen.tap(pt["x"], pt["y"])
    assert "Solo" in _popup_text(page)
    assert page.locator("#area-selection-dialog").count() == 0


def test_mouse_tolerance_is_tighter(served_map, browser):
    page = _open(browser, served_map, touch=False)
    far = _page_point(page, SOLO_LAT, 0.005, dy=14)
    page.mouse.click(far["x"], far["y"])
    page.wait_for_timeout(300)
    assert page.locator(".leaflet-popup-content").count() == 0

    near = _page_point(page, SOLO_LAT, 0.005, dy=4)
    page.mouse.click(near["x"], near["y"])
    assert "Solo" in _popup_text(page)


def test_tap_on_overlapping_tracks_lists_them(served_map, browser):
    page = _open(browser, served_map, touch=True)
    pt = _page_point(page, TWIN_LAT, 0.005, dy=10)
    page.touchscreen.tap(pt["x"], pt["y"])

    dialog = page.locator("#area-selection-dialog")
    dialog.wait_for(timeout=5000)
    assert "Activities here" in dialog.inner_text()
    assert dialog.locator("input[name='area-sel-mode']").count() == 0  # no rectangle modes
    names = dialog.locator(".area-sel-row span[title]").evaluate_all(
        "els => els.map(e => e.title)")
    assert names == ["Twin B", "Twin A"]  # newest first
    assert page.locator(".leaflet-popup-content").count() == 0

    # Narrowing the date range to exclude Twin B refreshes the list live.
    page.evaluate(
        "() => { currentDateRange = {start: '2024-01-01', end: '2024-05-15'};"
        " filterActivitiesByDateRange(); }"
    )
    page.wait_for_function(
        "() => document.querySelectorAll('#area-selection-dialog .area-sel-row').length === 1",
        timeout=5000,
    )

    # A row tap opens that activity's popup; closing the dialog clears the tap.
    dialog.locator(".area-sel-row").first.click()
    assert "Twin A" in _popup_text(page)
    page.click("#area-sel-close")
    assert page.locator("#area-selection-dialog").count() == 0
    assert page.evaluate("() => tapSelectLatLng") is None


def test_tap_on_empty_map_does_nothing(served_map, browser):
    page = _open(browser, served_map, touch=True)
    pt = _page_point(page, 0.0, 0.005)  # midway between the tracks, ~116 px from each
    page.touchscreen.tap(pt["x"], pt["y"])
    page.wait_for_timeout(300)
    assert page.locator(".leaflet-popup-content").count() == 0
    assert page.locator("#area-selection-dialog").count() == 0


def test_hidden_category_is_not_picked(served_map, browser):
    page = _open(browser, served_map, touch=True)
    page.locator(".leaflet-control-layers").get_by_text("Running", exact=True).click()
    pt = _page_point(page, SOLO_LAT, 0.005)
    page.touchscreen.tap(pt["x"], pt["y"])
    page.wait_for_timeout(300)
    assert page.locator(".leaflet-popup-content").count() == 0


def test_rectangle_drag_ending_on_tracks_keeps_area_dialog(served_map, browser):
    """The click the browser fires after a rectangle drag must not be taken as a tap."""
    page = _open(browser, served_map, touch=False)
    start = _page_point(page, SOLO_LAT + 0.005, -0.002)
    end = _page_point(page, TWIN_LAT, 0.005)  # released right on the twin tracks
    page.click(".leaflet-control-area-select")
    page.mouse.move(start["x"], start["y"])
    page.mouse.down()
    page.mouse.move(end["x"], end["y"], steps=8)
    page.mouse.up()

    dialog = page.locator("#area-selection-dialog")
    dialog.wait_for(timeout=5000)
    page.wait_for_timeout(300)
    assert "Selection" in dialog.inner_text()
    assert "Activities here" not in dialog.inner_text()
    assert dialog.locator(".area-sel-row").count() == 3


def _track_weight(page, name):
    return page.evaluate(
        """(name) => {
        let w = null;
        layerGroups['Running'].eachLayer(pl => {
            if (pl.activityData.name === name) w = pl.options.weight;
        });
        return w;
    }""",
        name,
    )


@pytest.mark.parametrize("touch", [True, False])
def test_closing_list_keeps_highlight_of_open_popup(served_map, browser, touch):
    """Closing the list must not un-highlight the track whose popup is still open."""
    page = _open(browser, served_map, touch=touch)
    pt = _page_point(page, TWIN_LAT, 0.005, dy=4)
    tap = page.touchscreen.tap if touch else page.mouse.click
    tap(pt["x"], pt["y"])

    dialog = page.locator("#area-selection-dialog")
    dialog.wait_for(timeout=5000)
    row = dialog.locator(".area-sel-row").first  # Twin B, newest first
    box = row.bounding_box()
    tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    assert "Twin B" in _popup_text(page)
    assert _track_weight(page, "Twin B") == 5

    close = page.locator("#area-sel-close").bounding_box()
    tap(close["x"] + close["width"] / 2, close["y"] + close["height"] / 2)
    assert page.locator("#area-selection-dialog").count() == 0
    assert page.locator(".leaflet-popup-content").count() == 1
    assert _track_weight(page, "Twin B") == 5

    # Closing the popup then drops the highlight as usual.
    page.evaluate("() => mapInstance.closePopup()")
    assert _track_weight(page, "Twin B") == 2


def _view(page):
    return page.evaluate(
        "() => { const c = mapInstance.getCenter();"
        " return [mapInstance.getZoom(), c.lat, c.lng]; }")


def _open_twin_list(page):
    pt = _page_point(page, TWIN_LAT, 0.005, dy=4)
    page.touchscreen.tap(pt["x"], pt["y"])
    dialog = page.locator("#area-selection-dialog")
    dialog.wait_for(timeout=5000)
    return dialog


def test_list_row_opens_popup_without_moving_map(served_map, browser):
    page = _open(browser, served_map, touch=True)
    dialog = _open_twin_list(page)
    before = _view(page)
    box = dialog.locator(".area-sel-row").nth(1).bounding_box()  # Twin A
    page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    assert "Twin A" in _popup_text(page)
    page.wait_for_timeout(300)  # let any pan/zoom animation run
    assert _view(page) == pytest.approx(before, abs=1e-9)


@pytest.mark.parametrize("where", ["track", "empty"])
def test_next_map_tap_closes_tap_list(served_map, browser, where):
    page = _open(browser, served_map, touch=True)
    _open_twin_list(page)
    lat = SOLO_LAT if where == "track" else 0.0
    pt = _page_point(page, lat, 0.005)
    page.touchscreen.tap(pt["x"], pt["y"])
    if where == "track":
        assert "Solo" in _popup_text(page)
    page.wait_for_function(
        "() => !document.getElementById('area-selection-dialog')", timeout=5000)
    assert page.evaluate("() => tapSelectLatLng") is None


def test_single_match_tap_keeps_rectangle_list(served_map, browser):
    page = _open(browser, served_map, touch=False)
    start = _page_point(page, SOLO_LAT + 0.005, -0.002)
    end = _page_point(page, TWIN_LAT - 0.005, 0.012)
    page.click(".leaflet-control-area-select")
    page.mouse.move(start["x"], start["y"])
    page.mouse.down()
    page.mouse.move(end["x"], end["y"], steps=8)
    page.mouse.up()
    dialog = page.locator("#area-selection-dialog")
    dialog.wait_for(timeout=5000)

    page.wait_for_timeout(600)  # past the post-drag click guard
    pt = _page_point(page, SOLO_LAT, 0.005)
    page.mouse.click(pt["x"], pt["y"])
    assert "Solo" in _popup_text(page)
    assert "Selection" in dialog.inner_text()

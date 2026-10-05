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

    # A row tap opens that activity's popup and keeps the list; closing the dialog
    # clears the tap.
    box = dialog.locator(".area-sel-row").first.bounding_box()
    page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    assert "Twin A" in _popup_text(page)
    assert page.locator("#area-selection-dialog").count() == 1
    close = page.locator("#area-sel-close").bounding_box()
    page.touchscreen.tap(close["x"] + close["width"] / 2, close["y"] + close["height"] / 2)
    assert page.locator("#area-selection-dialog").count() == 0
    assert page.evaluate("() => tapSelectLatLng") is None


def test_mouse_click_on_list_row_closes_tap_list(served_map, browser):
    page = _open(browser, served_map, touch=False)
    pt = _page_point(page, TWIN_LAT, 0.005)
    page.mouse.click(pt["x"], pt["y"])
    dialog = page.locator("#area-selection-dialog")
    dialog.wait_for(timeout=5000)

    dialog.locator(".area-sel-row").nth(1).click()  # Twin A (newest first)
    assert "Twin A" in _popup_text(page)
    assert page.locator("#area-selection-dialog").count() == 0
    assert page.evaluate("() => tapSelectLatLng") is None
    # The picked track stays highlighted and on top while its popup is open...
    assert _track_weight(page, "Twin A") == 5
    assert _topmost_track(page) == "Twin A"
    # ...and drops the highlight when the popup closes.
    page.evaluate("() => mapInstance.closePopup()")
    assert _track_weight(page, "Twin A") == 2


def _topmost_track(page):
    """Name of the track drawn last, i.e. on top of the others."""
    return page.evaluate(
        """() => {
        const paths = [...document.querySelectorAll('.leaflet-overlay-pane path')];
        const top = paths[paths.length - 1];
        let name = null;
        findLayerByName('Running').eachLayer(pl => {
            if (pl._path === top) name = pl.activityData.name;
        });
        return name;
    }"""
    )


def test_track_picked_from_list_stays_on_top(served_map, browser):
    # A rectangle list, since that one stays open after a mouse click on a row.
    page = _open(browser, served_map, touch=False)
    start = _page_point(page, TWIN_LAT + 0.002, -0.002)  # takes in both twins' start points
    end = _page_point(page, TWIN_LAT - 0.002, 0.012)
    page.click(".leaflet-control-area-select")
    page.mouse.move(start["x"], start["y"])
    page.mouse.down()
    page.mouse.move(end["x"], end["y"], steps=8)
    page.mouse.up()
    dialog = page.locator("#area-selection-dialog")
    dialog.wait_for(timeout=5000)

    rows = dialog.locator(".area-sel-row")
    assert rows.count() == 2
    rows.nth(1).click()  # Twin A (newest first)
    assert "Twin A" in _popup_text(page)
    rows.nth(0).hover()  # hovering Twin B raises it over Twin A...
    assert _topmost_track(page) == "Twin B"

    page.hover("#area-sel-close")  # ...until the pointer leaves its row
    assert _topmost_track(page) == "Twin A"
    page.click("#area-sel-close")
    assert _topmost_track(page) == "Twin A"
    assert page.evaluate("() => openPopupTrack.activityData.name") == "Twin A"


def test_tap_on_empty_map_does_nothing(served_map, browser):
    page = _open(browser, served_map, touch=True)
    pt = _page_point(page, 0.0, 0.005)  # midway between the tracks, ~116 px from each
    page.touchscreen.tap(pt["x"], pt["y"])
    page.wait_for_timeout(300)
    assert page.locator(".leaflet-popup-content").count() == 0
    assert page.locator("#area-selection-dialog").count() == 0


def test_hidden_category_is_not_picked(served_map, browser):
    page = _open(browser, served_map, touch=True)
    page.click("#type-filter-button")
    page.locator("#type-filter-menu label", has_text="Running").locator("input").click()
    page.keyboard.press("Escape")
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

    if touch:  # a mouse click on the row already closed the list
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
    page.wait_for_function(
        "() => !document.getElementById('area-selection-dialog')", timeout=5000)
    assert page.evaluate("() => tapSelectLatLng") is None
    # The same tap picks the track it lands on.
    if where == "track":
        assert "Solo" in _popup_text(page)
    else:
        page.wait_for_timeout(200)
        assert page.locator(".leaflet-popup").count() == 0


def test_map_tap_drops_rectangle_selection(served_map, browser):
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
    # The click drops the selection and opens the track it lands on.
    assert "Solo" in _popup_text(page)
    assert dialog.count() == 0
    assert page.evaluate("() => areaSelectBounds") is None
    assert page.locator(".area-select-handle").count() == 0


def _popup_box(page):
    return page.locator(".activity-popup .leaflet-popup-content-wrapper").bounding_box()


def _drag(page, touch, x, y, dx, dy):
    """Drag from (x, y) by (dx, dy) with the mouse, or with one finger over CDP."""
    steps = 8
    if not touch:
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + dx, y + dy, steps=steps)
        page.mouse.up()
        return
    cdp = page.context.new_cdp_session(page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    for i in range(1, steps + 1):
        cdp.send("Input.dispatchTouchEvent", {
            "type": "touchMove",
            "touchPoints": [{"x": x + dx * i / steps, "y": y + dy * i / steps}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


@pytest.mark.parametrize("touch", [False, True])
def test_popup_can_be_dragged_aside(served_map, browser, touch):
    page = _open(browser, served_map, touch=touch)
    pt = _page_point(page, SOLO_LAT, 0.005)
    (page.touchscreen.tap if touch else page.mouse.click)(pt["x"], pt["y"])
    assert "Solo" in _popup_text(page)
    tip = page.locator(".activity-popup .leaflet-popup-tip-container")
    assert tip.is_visible()
    before = _popup_box(page)
    view = _view(page)

    # Dragging anywhere but the title leaves the popup where it is...
    meta = page.locator(".activity-popup .ap-meta span").bounding_box()
    _drag(page, touch, meta["x"] + 5, meta["y"] + meta["height"] / 2, 80, -40)
    page.wait_for_timeout(300)
    # (released over the map, which must not take it as a click that closes the popup)
    assert page.locator(".leaflet-popup-content").count() == 1
    assert _popup_box(page) == pytest.approx(before, abs=1)
    assert tip.is_visible()

    # ...the title moves it.
    grab = page.locator(".activity-popup .ap-title").bounding_box()
    _drag(page, touch, grab["x"] + 5, grab["y"] + grab["height"] / 2, 80, -40)

    after = _popup_box(page)
    assert (after["x"] - before["x"], after["y"] - before["y"]) == pytest.approx((80, -40), abs=1)
    assert _view(page) == pytest.approx(view, abs=1e-9)  # the map itself didn't pan
    assert not tip.is_visible()                           # the tip no longer points at the track
    assert page.locator(".leaflet-popup-content").count() == 1

    # Zooming keeps the popup the same distance from its point on the track.
    anchor = _page_point(page, SOLO_LAT, 0.005)
    page.evaluate("() => mapInstance.setZoom(mapInstance.getZoom() + 1, {animate: false})")
    moved_anchor = _page_point(page, SOLO_LAT, 0.005)
    zoomed = _popup_box(page)
    assert (zoomed["x"] - moved_anchor["x"], zoomed["y"] - moved_anchor["y"]) == pytest.approx(
        (after["x"] - anchor["x"], after["y"] - anchor["y"]), abs=1)

    # The title still drags after the popup re-rendered its content.
    grab = page.locator(".activity-popup .ap-title").bounding_box()
    _drag(page, touch, grab["x"] + 5, grab["y"] + grab["height"] / 2, -30, 20)
    again = _popup_box(page)
    assert (again["x"] - zoomed["x"], again["y"] - zoomed["y"]) == pytest.approx((-30, 20), abs=1)

    # Reopened, the popup is back in its usual place with its tip.
    page.evaluate("() => mapInstance.closePopup()")
    page.evaluate("() => mapInstance.setZoom(mapInstance.getZoom() - 1, {animate: false})")
    (page.touchscreen.tap if touch else page.mouse.click)(pt["x"], pt["y"])
    assert "Solo" in _popup_text(page)
    assert _popup_box(page) == pytest.approx(before, abs=1)
    assert tip.is_visible()



TWIN_BOX = f"L.latLngBounds([[{TWIN_LAT - 0.003}, -0.002], [{TWIN_LAT + 0.003}, 0.012]])"


@pytest.mark.parametrize("touch", [False, True])
def test_rectangle_selection_survives_panning_resizing_and_the_controls(served_map, browser, touch):
    page = _open(browser, served_map, touch=touch)
    page.evaluate(f"() => setAreaSelection({TWIN_BOX})")
    dialog = page.locator("#area-selection-dialog")
    dialog.wait_for(timeout=5000)
    tap = page.touchscreen.tap if touch else page.mouse.click

    # Panning the map.
    empty = _page_point(page, 0.0, 0.005)
    _drag(page, touch, empty["x"], empty["y"], 60, 40)
    page.wait_for_timeout(300)
    assert dialog.count() == 1

    # Resizing the rectangle by a handle, and a press on a handle that doesn't move it.
    before = page.evaluate("() => areaSelectBounds.getEast()")
    handle = page.locator(".area-select-handle-e").bounding_box()
    _drag(page, touch, handle["x"] + handle["width"] / 2, handle["y"] + handle["height"] / 2, 40, 0)
    page.wait_for_timeout(300)
    assert dialog.count() == 1
    assert page.evaluate("() => areaSelectBounds.getEast()") > before
    handle = page.locator(".area-select-handle-e").bounding_box()
    tap(handle["x"] + handle["width"] / 2, handle["y"] + handle["height"] / 2)
    page.wait_for_timeout(300)
    assert dialog.count() == 1

    # The controls: the list follows their filters.
    page.click("#type-filter-button")
    page.click("#type-filter-button")
    assert dialog.count() == 1

    if touch:
        # A two-finger touch that doesn't move is not a tap either.
        cdp = page.context.new_cdp_session(page)
        points = [{"x": empty["x"], "y": empty["y"]}, {"x": empty["x"] + 80, "y": empty["y"]}]
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": points})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(300)
        assert dialog.count() == 1

    # A tap on the map closes it.
    empty = _page_point(page, SOLO_LAT + 0.004, 0.005)
    tap(empty["x"], empty["y"])
    page.wait_for_function("() => !document.getElementById('area-selection-dialog')", timeout=5000)
    assert page.evaluate("() => areaSelectBounds") is None


@pytest.mark.parametrize("touch", [False, True])
def test_tap_beside_the_tracks_keeps_a_popup_opened_from_the_list(served_map, browser, touch):
    page = _open(browser, served_map, touch=touch)
    page.evaluate(f"() => setAreaSelection({TWIN_BOX})")
    dialog = page.locator("#area-selection-dialog")
    dialog.wait_for(timeout=5000)
    row = dialog.locator(".area-sel-row").first.bounding_box()
    tap = page.touchscreen.tap if touch else page.mouse.click
    tap(row["x"] + 20, row["y"] + row["height"] / 2)
    name = _popup_text(page)

    empty = _page_point(page, 0.0, 0.005)
    tap(empty["x"], empty["y"])
    page.wait_for_function("() => !document.getElementById('area-selection-dialog')", timeout=5000)
    page.wait_for_timeout(200)
    assert page.locator(".leaflet-popup-content").inner_text() == name

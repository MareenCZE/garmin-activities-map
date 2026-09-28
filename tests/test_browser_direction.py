"""Headless-browser test for the direction shown on a highlighted track.

Hovering a track, opening its popup or hovering its row in the selection list
highlights it; while highlighted it carries chevrons pointing the way it was
recorded plus start and finish markers (a single marker when it is a loop).
Covers highlightTrack / showTrackDirection in
templates/activity_loader_template.html.

Opt-in: the module skips unless Playwright *and* a Chromium build are installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_direction.py
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


def _make_track(activity_id, name, coords, activity_type="running"):
    a = storage.Activity(activity_id, 5.0, 42.0, "2024-05-01", "07:30",
                          f"f{activity_id}", True, activity_type, name)
    a.coordinates = coords
    return a


# Near Null Island: "Eastbound" runs west to east along lat 0.01; "Loop" goes
# round a small square and ends where it started.
EAST_LAT = 0.010
LOOP = [[-0.010, 0.000], [-0.010, 0.010], [-0.018, 0.010], [-0.018, 0.000], [-0.010, 0.000]]
# Not shown on load (Inline is off): an out-and-back along lat 0.02, and three
# laps of the loop square.
OUT_AND_BACK = [[0.020, 0.000], [0.020, 0.010], [0.020, 0.000]]
LAPS = LOOP + LOOP[1:] + LOOP[1:]


@pytest.fixture
def page(config, tmp_path):
    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["mapy-com-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 14
    config["map-tiles"]["center-point"] = [0.0, 0.005]
    config["activities"]["display-mapping-on-load"] = ["Running"]
    config["activities"]["enable-activity-highlighting"] = True

    tracks = [
        _make_track(1, "Eastbound", [[EAST_LAT, 0.000], [EAST_LAT, 0.010]]),
        _make_track(2, "Loop", LOOP),
        _make_track(3, "Out and back", OUT_AND_BACK, "inline_skating"),
        _make_track(4, "Laps", LAPS, "inline_skating"),
    ]
    mapgenerator.create_map_with_activities(tracks, str(tmp_path / "activities_map.html"))

    port = _free_port()
    handler = functools.partial(_QuietHandler, directory=str(tmp_path))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as exc:  # browser binary not installed
                pytest.skip(f"Chromium not available: {exc}")
            try:
                page = browser.new_page(viewport={"width": 1024, "height": 700})
                page.goto(f"http://127.0.0.1:{port}/activities_map.html")
                page.wait_for_function(
                    "() => typeof activityData === 'object' && (activityData['Running'] || []).length === 2",
                    timeout=20000,
                )
                yield page
            finally:
                browser.close()
    finally:
        httpd.shutdown()


def _fire(page, name, event):
    page.evaluate(
        """([name, event]) => layerGroups['Running'].eachLayer(pl => {
            if (pl.activityData.name === name) pl.fire(event);
        })""",
        [name, event],
    )


def _direction(page):
    """Per shown track: its chevron count and end-marker kinds."""
    return page.evaluate(
        """() => {
        const out = {};
        trackDirections.forEach((d, pl) => {
            const ends = [];
            d.markers.eachLayer(m => ends.push(m.options.icon.options.className.split('track-end-')[1]));
            out[pl.activityData.name] = { chevrons: d.chevrons.getLayers().length, ends: ends.sort() };
        });
        return out;
    }"""
    )


def test_hover_shows_chevrons_and_start_finish(page):
    assert _direction(page) == {}
    _fire(page, "Eastbound", "mouseover")
    shown = _direction(page)
    assert shown["Eastbound"]["chevrons"] > 0
    assert shown["Eastbound"]["ends"] == ["finish", "start"]
    assert page.locator(".track-end").count() == 2

    _fire(page, "Eastbound", "mouseout")
    assert _direction(page) == {}
    assert page.locator(".track-end").count() == 0


def test_chevrons_point_the_recorded_way(page):
    _fire(page, "Eastbound", "mouseover")
    # Each chevron is [arm, tip, arm]; on a west-to-east track the tip is east of both arms.
    chevrons = page.evaluate(
        """() => { const r = [];
        trackDirections.forEach(d => d.chevrons.eachLayer(c => r.push(c.getLatLngs().map(ll => ll.lng))));
        return r; }"""
    )
    assert chevrons
    for arm1, tip, arm2 in chevrons:
        assert tip > arm1 and tip > arm2


def test_loop_gets_one_combined_marker(page):
    _fire(page, "Loop", "mouseover")
    assert _direction(page)["Loop"]["ends"] == ["loop"]


def _open_popup(page, name):
    page.evaluate(
        """name => layerGroups['Running'].eachLayer(pl => {
            if (pl.activityData.name === name) pl.openPopup(pl.getLatLngs()[0]);
        })""",
        name,
    )


def _highlighted(page):
    return sorted(page.evaluate(
        "() => { const r = []; layerGroups['Running'].eachLayer(pl => {"
        " if (pl.options.color === '#00FF00') r.push(pl.activityData.name); }); return r; }"))


def test_open_popup_keeps_direction_until_closed(page):
    _open_popup(page, "Eastbound")
    _fire(page, "Eastbound", "mouseout")  # leaving the line keeps the open track's direction
    assert set(_direction(page)) == {"Eastbound"}

    page.evaluate("() => mapInstance.closePopup()")
    assert _direction(page) == {}


def test_hover_ignores_other_tracks_while_popup_open(page):
    _open_popup(page, "Eastbound")
    _fire(page, "Loop", "mouseover")
    assert _highlighted(page) == ["Eastbound"]
    assert set(_direction(page)) == {"Eastbound"}
    _fire(page, "Loop", "mouseout")
    assert _highlighted(page) == ["Eastbound"]

    # Once the popup is closed, hovering works again.
    page.evaluate("() => mapInstance.closePopup()")
    _fire(page, "Loop", "mouseover")
    assert _highlighted(page) == ["Loop"]


def test_show_direction_setting(page):
    _fire(page, "Eastbound", "mouseover")
    page.click(".leaflet-control-display-settings")
    assert page.is_checked("#show-direction-toggle")

    page.uncheck("#show-direction-toggle")  # applies to the track already highlighted
    assert _direction(page) == {}
    _fire(page, "Eastbound", "mouseout")
    _fire(page, "Loop", "mouseover")
    assert _direction(page) == {}
    assert _highlighted(page) == ["Loop"]   # still highlighted, just no direction

    page.check("#show-direction-toggle")
    assert set(_direction(page)) == {"Loop"}

    # Remembered across a reload.
    page.uncheck("#show-direction-toggle")
    page.reload()
    page.wait_for_function("() => (activityData['Running'] || []).length === 2", timeout=20000)
    _fire(page, "Loop", "mouseover")
    assert _direction(page) == {}


def test_chevrons_rebuilt_at_new_zoom(page):
    _fire(page, "Eastbound", "mouseover")
    before = _direction(page)["Eastbound"]["chevrons"]
    page.evaluate("() => mapInstance.setZoom(mapInstance.getZoom() + 1, { animate: false })")
    after = _direction(page)["Eastbound"]["chevrons"]
    # Spaced in screen pixels, so twice the on-screen length carries about twice as many.
    assert after >= 2 * before - 1


def test_mouse_click_on_highlighted_track_opens_popup(page):
    # Regression: redrawing the track under the pointer on every mouseover used to
    # swallow the click, so hovering a track made it unclickable.
    pt = page.evaluate(
        f"""() => {{
        const p = mapInstance.latLngToContainerPoint([{EAST_LAT}, 0.005]);
        const rect = mapInstance.getContainer().getBoundingClientRect();
        return {{x: rect.left + p.x, y: rect.top + p.y}};
    }}"""
    )
    page.mouse.move(pt["x"], pt["y"])
    page.mouse.click(pt["x"], pt["y"])
    popup = page.locator(".leaflet-popup-content")
    popup.wait_for(timeout=5000)
    assert "Eastbound" in popup.inner_text()
    assert "Eastbound" in _direction(page)


def _chevrons(page, category, name):
    """The shown track's chevrons as screen points [arm, tip, arm]."""
    return page.evaluate(
        """([category, name]) => {
        let track = null;
        layerGroups[category].eachLayer(pl => { if (pl.activityData.name === name) track = pl; });
        track.fire('mouseover');
        const r = [];
        trackDirections.get(track).chevrons.eachLayer(c =>
            r.push(c.getLatLngs().map(ll => { const p = mapInstance.latLngToLayerPoint(ll); return [p.x, p.y]; })));
        return r;
    }""",
        [category, name],
    )


def _show_inline(page):
    page.evaluate("() => mapInstance.addLayer(layerGroups['Inline'])")
    page.wait_for_function("() => (activityData['Inline'] || []).length === 2", timeout=20000)


def test_out_and_back_shows_both_directions_on_the_line(page):
    _show_inline(page)
    line_y = page.evaluate("() => mapInstance.latLngToLayerPoint([0.020, 0.005]).y")
    chevrons = _chevrons(page, "Inline", "Out and back")
    east = [c for c in chevrons if c[1][0] > c[0][0]]
    west = [c for c in chevrons if c[1][0] < c[0][0]]
    assert east and west  # opposite directions are not treated as repeats
    assert all(abs(c[1][1] - line_y) < 1 for c in chevrons)


def test_laps_do_not_repeat_chevrons(page):
    _show_inline(page)
    one_lap = len(_chevrons(page, "Running", "Loop"))
    three_laps = len(_chevrons(page, "Inline", "Laps"))
    assert 0 < three_laps <= one_lap + 1

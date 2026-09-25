"""Headless-browser test for the date-range filter panel.

The panel at the top of the map pairs the noUiSlider with a preset dropdown
("This year", "Last month", one entry per year, ...) and two date fields. All
three stay in sync and filter the tracks; the chosen preset is remembered in
localStorage. Covers initializeDateRangeSlider and the day-number helpers in
templates/activity_loader_template.html.

The browser clock is frozen at TODAY and the timezone set well east of UTC, where
turning local midnight into an ISO date used to land on the previous day.

Opt-in: the module skips unless Playwright *and* a Chromium build are installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_date_range.py
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

TODAY = "2025-06-20T10:00:00"
TIMEZONE = "Pacific/Auckland"


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _make_track(activity_id, name, lat, date):
    a = storage.Activity(activity_id, 5.0, 42.0, date, "07:30",
                          f"f{activity_id}", True, "running", name)
    a.coordinates = [[lat, 0.000], [lat, 0.010]]
    return a


@pytest.fixture
def served_map(config, tmp_path):
    """Four running tracks near Null Island, spread over 2024 and 2025."""
    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["mapy-com-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 14
    config["map-tiles"]["center-point"] = [0.0, 0.005]
    config["activities"]["display-mapping-on-load"] = ["Running"]

    tracks = [
        _make_track(1, "March", 0.000, "2024-03-10"),
        _make_track(2, "New Year's Eve", 0.002, "2024-12-31"),
        _make_track(3, "New Year", 0.004, "2025-01-01"),
        _make_track(4, "June", 0.006, "2025-06-15"),
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
def context():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:  # browser binary not installed
            pytest.skip(f"Chromium not available: {exc}")
        try:
            ctx = b.new_context(timezone_id=TIMEZONE)
            ctx.clock.set_fixed_time(TODAY)
            yield ctx
        finally:
            b.close()


def _open(context, url):
    page = context.new_page()
    page.goto(url)
    page.wait_for_function(
        "() => typeof activityData === 'object' && (activityData['Running'] || []).length === 4"
        " && dateSlider !== null",
        timeout=20000,
    )
    return page


def _state(page):
    """What the panel shows, and which tracks are on the map."""
    return page.evaluate(
        """() => {
        const names = [];
        findLayerByName('Running').eachLayer(pl => names.push(pl.activityData.name));
        return {
            preset: document.getElementById('date-range-preset').value,
            start: document.getElementById('date-range-start').value,
            end: document.getElementById('date-range-end').value,
            slider: dateSlider.noUiSlider.get().map(v => dayToIsoDate(Math.round(+v))),
            shown: names.sort(),
        };
    }"""
    )


def test_starts_at_all_time(served_map, context):
    page = _open(context, served_map)
    s = _state(page)
    assert s["preset"] == "all"
    assert (s["start"], s["end"]) == ("2024-03-10", "2025-06-15")
    assert s["slider"] == ["2024-03-10", "2025-06-15"]
    assert len(s["shown"]) == 4


def test_year_entries_come_from_the_data(served_map, context):
    page = _open(context, served_map)
    years = page.locator("#date-range-preset optgroup option").evaluate_all(
        "els => els.map(e => e.value)")
    assert years == ["year-2025", "year-2024"]


@pytest.mark.parametrize("preset, start, end, shown", [
    # Clamped to the data: the year runs on past the last activity.
    ("this-year", "2025-01-01", "2025-06-15", ["June", "New Year"]),
    ("last-year", "2024-03-10", "2024-12-31", ["March", "New Year's Eve"]),
    ("year-2024", "2024-03-10", "2024-12-31", ["March", "New Year's Eve"]),
    ("last-12-months", "2024-06-21", "2025-06-15", ["June", "New Year", "New Year's Eve"]),
    ("last-30-days", "2025-05-22", "2025-06-15", ["June"]),
    ("this-month", "2025-06-01", "2025-06-15", ["June"]),
    # No activity in May: the range is kept as it is and nothing is shown.
    ("last-month", "2025-05-01", "2025-05-31", []),
])
def test_presets(served_map, context, preset, start, end, shown):
    page = _open(context, served_map)
    page.select_option("#date-range-preset", preset)
    s = _state(page)
    assert s["preset"] == preset
    assert (s["start"], s["end"]) == (start, end)
    assert s["shown"] == sorted(shown)


def test_preset_past_the_data_parks_the_handles_at_the_edge(served_map, context):
    context.clock.set_fixed_time("2025-09-10T10:00:00")  # "last month" = August
    page = _open(context, served_map)
    page.select_option("#date-range-preset", "last-month")
    s = _state(page)
    assert (s["start"], s["end"]) == ("2025-08-01", "2025-08-31")
    assert s["slider"] == ["2025-06-15", "2025-06-15"]
    assert s["shown"] == []


def test_date_fields_make_a_custom_range(served_map, context):
    page = _open(context, served_map)
    page.fill("#date-range-start", "2024-12-31")
    page.fill("#date-range-end", "2025-01-01")
    s = _state(page)
    assert s["preset"] == "custom"
    assert s["slider"] == ["2024-12-31", "2025-01-01"]
    assert s["shown"] == ["New Year", "New Year's Eve"]

    # Moving the start past the end drags the end along.
    page.fill("#date-range-start", "2025-02-01")
    s = _state(page)
    assert (s["start"], s["end"]) == ("2025-02-01", "2025-02-01")
    assert s["shown"] == []


def test_slider_drag_makes_a_custom_range(served_map, context):
    page = _open(context, served_map)
    page.select_option("#date-range-preset", "this-year")
    page.focus("#date-range-slider .noUi-handle-lower")
    page.keyboard.press("ArrowLeft")  # one day back
    s = _state(page)
    assert s["preset"] == "custom"
    assert s["start"] == "2024-12-31"
    assert s["shown"] == ["June", "New Year", "New Year's Eve"]


def test_preset_is_remembered_but_custom_is_not(served_map, context):
    page = _open(context, served_map)
    page.select_option("#date-range-preset", "last-year")
    page = _open(context, served_map)
    assert _state(page)["preset"] == "last-year"

    page.fill("#date-range-end", "2024-06-01")
    page = _open(context, served_map)
    assert _state(page)["preset"] == "all"


def test_unusable_saved_preset_falls_back_to_all_time(served_map, context):
    page = _open(context, served_map)
    page.evaluate("() => localStorage.setItem('activitiesMap.datePreset', 'year-1999')")
    page = _open(context, served_map)
    assert _state(page)["preset"] == "all"


def test_day_helpers(served_map, context):
    page = _open(context, served_map)
    r = page.evaluate(
        """() => ({
        roundTrip: dayToIsoDate(isoDateToDay('2024-02-29')),
        empty: isoDateToDay(''),
        garbage: isoDateToDay('not-a-date'),
        impossible: isoDateToDay('2024-02-31'),
        consecutive: isoDateToDay('2025-01-01') - isoDateToDay('2024-12-31'),
    })"""
    )
    assert r == {"roundTrip": "2024-02-29", "empty": None, "garbage": None,
                 "impossible": None, "consecutive": 1}

"""Headless-browser test for saving a selected rectangle as an image.

The selection dialog of a rectangle has a "Save image" footer that redraws the
rectangle on a canvas at a higher zoom (saveMapImage in
templates/activity_loader_template.html): the base map's tiles for that zoom,
the tracks that are visible now, and the tile attribution. The tile server is
faked here with page.route, so no real tiles are downloaded.

Opt-in: the module skips unless Playwright *and* a Chromium build are installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_image_export.py
"""
import base64
import functools
import http.server
import socket
import socketserver
import struct
import threading
import zlib

import pytest

pytest.importorskip("playwright.sync_api")  # skip module if Playwright is absent

import mapgenerator
import storage

TILE_RGB = (200, 230, 200)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _solid_png(rgb, size=256):
    """A plain one-colour PNG, built by hand so the test needs no imaging library."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    row = b"\x00" + bytes(rgb) * size
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * size))
            + chunk(b"IEND", b""))


def _make_track(activity_id, name, coords, activity_type):
    a = storage.Activity(activity_id, 5.0, 42.0, "2024-05-01", "07:30",
                          f"f{activity_id}", True, activity_type, name)
    a.coordinates = coords
    return a


@pytest.fixture
def served_map(config, tmp_path):
    """Two tracks near Null Island: a Running one along lat 0.000 and a Cycling one along lat 0.004."""
    config["map-tiles"]["tiles"] = [{"tiles": "OpenStreetMap", "name": "OSM"}]
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["mapy-com-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 14
    config["map-tiles"]["center-point"] = [0.0, 0.005]
    config["activities"]["display-mapping-on-load"] = ["Running", "Cycling"]

    tracks = [
        _make_track(1, "Easy run", [[0.000, 0.000], [0.000, 0.010]], "running"),
        _make_track(2, "Short ride", [[0.004, 0.000], [0.004, 0.010]], "cycling"),
    ]
    mapgenerator.create_map_with_activities(tracks, str(tmp_path / "activities_map.html"))

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


def _open(browser, url, tiles_fail=False):
    """A page with the OSM tile server faked; returns (page, list of requested tile URLs).

    A tile that the browser may not read (no CORS headers) fails the same way as
    one that doesn't load, so failing tiles are simulated by aborting them.
    Playwright's route.fulfill adds CORS headers by itself, so it can't fake them.
    """
    page = browser.new_page(accept_downloads=True)
    requested = []
    png = _solid_png(TILE_RGB)

    def serve_tile(route):
        requested.append(route.request.url)
        if tiles_fail:
            route.abort()
        else:
            route.fulfill(status=200, content_type="image/png", body=png,
                          headers={"access-control-allow-origin": "*"})

    page.route("https://tile.openstreetmap.org/**", serve_tile)
    page.goto(url)
    page.wait_for_selector(".leaflet-control-area-select", timeout=20000)
    page.wait_for_function(
        "() => (activityData['Running'] || []).length === 1 && (activityData['Cycling'] || []).length === 1",
        timeout=20000,
    )
    return page, requested


def _select_box(page):
    """Drag a rectangle over [-0.002..0.006, 0.002..0.008]; returns its size on screen in px."""
    box = page.evaluate(
        """() => {
        const rect = mapInstance.getContainer().getBoundingClientRect();
        const nw = mapInstance.latLngToContainerPoint([0.006, 0.002]);
        const se = mapInstance.latLngToContainerPoint([-0.002, 0.008]);
        return {x1: rect.left + nw.x, y1: rect.top + nw.y, x2: rect.left + se.x, y2: rect.top + se.y};
    }"""
    )
    page.click(".leaflet-control-area-select")
    page.mouse.move(box["x1"], box["y1"])
    page.mouse.down()
    page.mouse.move(box["x2"], box["y2"], steps=8)
    page.mouse.up()
    page.wait_for_selector("#image-export-save", timeout=10000)
    return box["x2"] - box["x1"], box["y2"] - box["y1"]


def _pixel_stats(page, png_bytes):
    """Size of the PNG and how many of its pixels are tile, Running or Cycling coloured."""
    data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode()
    return page.evaluate(
        """async (src) => {
        const img = new Image();
        img.src = src;
        await img.decode();
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        const near = (i, r, g, b) => Math.abs(d[i] - r) < 30 && Math.abs(d[i + 1] - g) < 30 && Math.abs(d[i + 2] - b) < 30;
        let tile = 0, running = 0, cycling = 0;
        for (let i = 0; i < d.length; i += 4) {
            if (near(i, 200, 230, 200)) tile++;
            // Tracks are 80 % opaque over the tile: magenta and blueviolet blended.
            if (near(i, 244, 46, 244)) running++;
            if (near(i, 150, 82, 221)) cycling++;
        }
        return {width: img.naturalWidth, height: img.naturalHeight, tile, running, cycling};
    }""",
        data_url,
    )


def _save(page, zoom_factor_label):
    """Pick the option starting with the label, save, and return the downloaded bytes."""
    select = page.locator("#image-export-zoom")
    value = select.locator("option", has_text=zoom_factor_label).first.get_attribute("value")
    select.select_option(value)
    with page.expect_download(timeout=20000) as info:
        page.click("#image-export-save")
    with open(info.value.path(), "rb") as fh:
        return info.value.suggested_filename, fh.read()


def test_saved_image_has_more_detail_and_only_visible_tracks(served_map):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page, requested = _open(browser, served_map)
            # Hide Cycling: the image must follow the type filter.
            page.click("#type-filter-button")
            page.locator("#type-filter-menu label", has_text="Cycling").locator("input").click()
            page.keyboard.press("Escape")

            width, height = _select_box(page)
            requested.clear()
            name, png = _save(page, "2× detail")

            assert name.endswith("-z15.png")
            stats = _pixel_stats(page, png)
            assert abs(stats["width"] - 2 * width) <= 2
            assert abs(stats["height"] - 2 * height) <= 2
            assert stats["tile"] > 0
            assert stats["running"] > 0
            assert stats["cycling"] == 0
            # The tiles are fetched at the export zoom, not the screen's.
            assert requested and all("/15/" in url for url in requested)
            assert "Saved" in page.locator("#image-export-status").inner_text()
        finally:
            browser.close()


def test_zoom_choices_stop_at_the_base_map_limits(served_map):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page, _ = _open(browser, served_map)
            _select_box(page)
            options = page.locator("#image-export-zoom option")
            labels = options.all_inner_texts()
            assert labels[0].startswith("As on screen")
            # A small rectangle can go up to the base map's last zoom (OSM: 19).
            assert options.last.get_attribute("value") == "19"
            assert not any(options.nth(i).is_disabled() for i in range(len(labels)))

            # A large area stops at the first zoom that is too large, listed disabled.
            choices = page.evaluate(
                """() => imageExportChoices(L.latLngBounds([-0.5, -0.5], [0.5, 0.5]), activeBaseLayer())
                    .map(c => ({z: c.plan.z, fits: c.fits, tiles: c.plan.tiles}))"""
            )
            assert [c["fits"] for c in choices] == [True] * (len(choices) - 1) + [False]
            assert choices[-1]["z"] < 19
        finally:
            browser.close()


def test_tiles_that_fail_report_an_error(served_map):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page, _ = _open(browser, served_map, tiles_fail=True)
            _select_box(page)
            page.click("#image-export-save")
            page.wait_for_function(
                "() => document.getElementById('image-export-status').textContent.startsWith('Could not save')",
                timeout=20000,
            )
            assert "map tiles could not be loaded" in page.locator("#image-export-status").inner_text()
            assert not page.locator("#image-export-save").is_disabled()
        finally:
            browser.close()

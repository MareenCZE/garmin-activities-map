"""Headless-browser test for saving an image of the map.

The camera button's "Save image" panel redraws the selection, or the current
view without one, on a canvas at a higher zoom (saveMapImage in
templates/activity_loader_template.html): the base map's tiles for that zoom,
the tracks, and the tile attribution; with "No map" the tracks alone on a
transparent background. A preset can set the selection and the image zoom. The
tile server is faked here with page.route, so no real tiles are downloaded.

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

# A preset with a selection around the two tracks, saved at a zoom below the map's
# (14), named so its file name is checked.
PRESETS = [
    {"name": "Null Island run", "selection": [[-0.002, 0.002], [0.006, 0.008]], "image-zoom": 13},
]

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
    config.pop("image-presets", None)
    config["presets"] = PRESETS

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
    page.click("#area-sel-save-image")  # opens the Save image panel on the rectangle
    page.wait_for_selector("#image-export-dialog:not([hidden])", timeout=10000)
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
        let tile = 0, fadedTile = 0, running = 0, cycling = 0, clear = 0, magenta = 0;
        const columnGreen = [];
        for (let i = 0; i < d.length; i += 4) {
            // The tile, plain and at 50 % over the white ground of a faded map: close
            // colours, so matched tightly.
            const exact = (r, g, b) => Math.abs(d[i] - r) < 6 && Math.abs(d[i + 1] - g) < 6 && Math.abs(d[i + 2] - b) < 6;
            if (exact(200, 230, 200)) tile++;
            if (exact(228, 243, 228)) fadedTile++;
            // Tracks are 80 % opaque over the tile: magenta and blueviolet blended.
            if (near(i, 244, 46, 244)) running++;
            if (near(i, 150, 82, 221)) cycling++;
            if (d[i + 3] === 0) clear++;
            // Magenta at any opacity and over anything, for the transparent images.
            if (d[i + 3] > 0 && d[i] > 200 && d[i + 1] < 80 && d[i + 2] > 200) magenta++;
            // Above the attribution, which spans the bottom of a small image.
            const x = (i / 4) % canvas.width, y = Math.floor(i / 4 / canvas.width);
            if (x === (canvas.width >> 1) && y < canvas.height - 40) columnGreen.push(d[i + 1]);
        }
        // Line thickness: how much the (horizontal) tracks darken the middle column's
        // green below the background, summed. Grows with the width, blur or not.
        const ground = Math.max(...columnGreen);
        const inkInColumn = columnGreen.reduce((sum, g) => sum + (ground - g) / ground, 0);
        return {width: img.naturalWidth, height: img.naturalHeight, tile, fadedTile, running, cycling, clear, magenta,
                inkInColumn};
    }""",
        data_url,
    )


def _save(page, zoom_factor_label=None):
    """Pick the zoom option with the label (if any), save, and return the downloaded file."""
    if zoom_factor_label:
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


def _hide_type(page, name):
    page.click("#type-filter-button")
    page.locator("#type-filter-menu label", has_text=name).locator("input").click()
    page.keyboard.press("Escape")


def test_saves_the_current_view_without_a_selection(served_map):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page, _ = _open(browser, served_map)
            page.click(".leaflet-control-image-export")
            page.wait_for_selector("#image-export-dialog:not([hidden])", timeout=10000)
            assert page.locator("#image-export-show").is_hidden()
            assert "The current view" in page.locator("#image-export-status").inner_text()
            name, png = _save(page, "As on screen")
            size = page.evaluate("() => mapInstance.getSize()")
            stats = _pixel_stats(page, png)
            assert abs(stats["width"] - size["x"]) <= 1 and abs(stats["height"] - size["y"]) <= 1
            assert stats["running"] > 0 and stats["cycling"] > 0
            assert name.startswith("activities-map-")

            # Moving the map changes what is saved.
            page.evaluate("() => mapInstance.setZoom(15)")
            page.wait_for_function(
                "() => document.getElementById('image-export-status').textContent.includes('zoom 1')", timeout=10000)
            # The chosen detail stays chosen; "as on screen" is the new zoom.
            assert page.locator("#image-export-zoom").input_value() == "14"
            on_screen = page.locator("#image-export-zoom option", has_text="As on screen")
            assert on_screen.get_attribute("value") == "15"
        finally:
            browser.close()


def test_transparent_background_with_no_map(served_map):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page, requested = _open(browser, served_map)
            page.select_option("#tile-layer-select", label="No map")
            _select_box(page)
            assert "no map tiles" in page.locator("#image-export-status").inner_text()
            # Without tiles to download, zooms past OSM's last one are offered.
            last = page.locator("#image-export-zoom option").last
            assert last.get_attribute("value") == "22" or last.inner_text().endswith("too large")
            requested.clear()
            name, png = _save(page, "2× detail")
            assert name.endswith("-transparent.png")
            stats = _pixel_stats(page, png)
            assert stats["tile"] == 0 and stats["clear"] > 0 and stats["magenta"] > 0
            assert requested == []
        finally:
            browser.close()


def test_preset_selection_and_image_zoom(served_map):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page, requested = _open(browser, served_map)
            page.click(".leaflet-control-presets")
            page.locator("#presets-list .preset-item", has_text="Null Island run").click()
            page.click(".leaflet-control-image-export")
            # The preset's image zoom is chosen, though below the map's.
            assert page.locator("#image-export-zoom").input_value() == "13"
            assert page.locator("#image-export-zoom option:checked").inner_text().startswith("1/2 of the detail")

            requested.clear()
            name, png = _save(page)
            assert name.startswith("null-island-run-") and name.endswith("-z13.png")
            stats = _pixel_stats(page, png)
            width, height, _ = mapgenerator.image_size(PRESETS[0]["selection"], 13)
            assert (stats["width"], stats["height"]) == (width, height)
            assert requested and all("/13/" in url for url in requested)

            # A selection drawn by hand is no longer the preset's: the file name says so.
            page.click("#image-export-close")
            _select_box(page)
            name, _ = _save(page)
            assert name.startswith("activities-map-")
        finally:
            browser.close()

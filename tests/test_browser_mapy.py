"""Headless-browser test for the client-side Mapy.com attribution toggle.

This is the one piece of behaviour that pure-Python tests can't cover: the
JavaScript in templates/activity_loader_template.html that shows the Mapy.com
logo control only while a Mapy.com base layer is active.

It builds a real map (OSM default + a Mapy.com layer with a dummy key), serves
it over http, drives it in headless Chromium and checks the toggle.

Opt-in: the whole module skips unless Playwright *and* a Chromium build are
installed. To run it:

    pip install playwright && playwright install chromium
    python -m pytest tests/test_browser_mapy.py
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


@pytest.fixture
def served_map(config, tmp_path):
    """Build a map (OSM + a keyed Mapy.com layer) and serve it; yield its URL."""
    config["map-tiles"]["tiles"] = [
        {"tiles": "OpenStreetMap", "name": "OSM"},
        {"tiles": "mapy.com-winter", "name": "Mapy Winter"},
    ]
    config["map-tiles"]["mapy-com-api-key"] = "DUMMYKEY"  # builds the layer; tiles 403, irrelevant
    config["map-tiles"]["carto-api-key"] = ""
    config["map-tiles"]["zoom-start"] = 8
    config["activities"]["display-mapping-on-load"] = ["Running"]

    activity = storage.Activity(1, 5, 30, "2024-05-01", "07:30", "x", False, "running", "R")
    activity.coordinates = [[50.0, 14.0], [50.1, 14.1]]

    out_html = tmp_path / "activities_map.html"
    mapgenerator.create_map_with_activities([activity], str(out_html))

    port = _free_port()
    handler = functools.partial(_QuietHandler, directory=str(tmp_path))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{port}/activities_map.html"
    finally:
        httpd.shutdown()


def _display(page, selector):
    return page.eval_on_selector(selector, "el => getComputedStyle(el).display")


def test_mapy_logo_toggles_with_active_base_layer(served_map):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # browser binary not installed
            pytest.skip(f"Chromium not available: {exc}")

        try:
            page = browser.new_page()
            page.goto(served_map)

            # loader waits ~2s then wires the map + controls
            page.wait_for_selector(".leaflet-control-layers", timeout=20000)
            page.wait_for_selector(".mapy-attribution", state="attached", timeout=20000)

            # OSM is the default base layer -> Mapy logo hidden
            assert _display(page, ".mapy-attribution") == "none"

            # switch to the Mapy.com base layer -> logo appears
            page.get_by_text("Mapy Winter", exact=True).click()
            page.wait_for_function(
                "getComputedStyle(document.querySelector('.mapy-attribution')).display === 'flex'",
                timeout=10000,
            )
            assert _display(page, ".mapy-attribution") == "flex"
            assert page.eval_on_selector(".mapy-attribution img", "el => el.getAttribute('src')") \
                == "https://api.mapy.com/img/api/logo.svg"
            assert page.eval_on_selector(".mapy-attribution a", "el => el.getAttribute('href')") \
                == "https://mapy.com/"
            # the logo sits in the bottom-right corner, directly above the attribution control
            assert page.evaluate(
                "document.querySelector('.mapy-attribution').nextElementSibling"
                ".classList.contains('leaflet-control-attribution')")
            assert page.eval_on_selector(".mapy-attribution", "el => !!el.closest('.leaflet-bottom.leaflet-right')")
            # the copyright lives in Leaflet's attribution control only - not duplicated
            assert page.evaluate(
                "document.body.innerText.split('Seznam.cz a.s. and others').length - 1") == 1
            assert page.eval_on_selector(
                ".leaflet-control-attribution a[href='https://api.mapy.com/copyright']",
                "el => el.textContent") == "Seznam.cz a.s. and others"

            # switch back to OSM -> logo hidden again
            page.get_by_text("OSM", exact=True).click()
            page.wait_for_function(
                "getComputedStyle(document.querySelector('.mapy-attribution')).display === 'none'",
                timeout=10000,
            )
            assert _display(page, ".mapy-attribution") == "none"
        finally:
            browser.close()

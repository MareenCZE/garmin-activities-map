# Tests

Unit/integration tests for the activities-map pipeline. They exercise the pure
logic and data transformations (CSV database, coordinate simplification, API
response mapping, category grouping, map/data-file generation, FTP upload
decisions) without touching Garmin Connect or a real FTP server — network I/O is
mocked.

## Running

From the project root:

```bash
python -m pytest
```

`conftest.py` chdirs to the project root so `common.load_config()` finds
`config-default.toml`, and redirects storage/output at a tmp dir per test, so the
suite never reads or writes your real `data/` or `output/` trees.

## Dependencies

Install the runtime and test dependencies into a virtual environment:

```bash
pip install -r requirements-dev.txt
```

For Python coverage: `coverage run -m pytest && coverage report -m`.

## Browser tests

The `test_browser_*.py` modules build a real map, serve it locally and drive it in
headless Chromium to test the client-side JavaScript in
`templates/activity_loader_template.html`, which pure-Python tests can't reach. They
**skip** unless Playwright and a Chromium build are present, so a green run does not by
itself mean they ran; pytest then ends with a warning naming what is missing:

```bash
playwright install chromium
python -m pytest tests/test_browser_*.py
```

## Layout

- `test_common.py` — recursive config merge + loaded-config shape
- `test_storage.py` — `Activity` model, CSV read/write round-trip, resort/delete/update
- `test_downloader.py` — `map_to_object` (both Garmin response shapes), datetime
  parsing, GPX simplification, incremental download (mocked API)
- `test_mapgenerator.py` — category mapping, popup HTML, per-category data files +
  manifest, and an end-to-end map build
- `test_ftpuploader.py` — Fernet round-trip, size-based upload decisions, and the
  incremental upload flow (mocked `ftplib.FTP`)
- `test_cli.py` — command-line options overriding the `[mode]` config
- `test_browser_mapy.py` — headless-Chromium check of the Mapy.com logo toggle
  (opt-in; see above)
- `test_browser_area_select.py`, `test_browser_tap_select.py` — headless-Chromium
  checks of the rectangle selection tool (drawing and resizing, by mouse and touch)
  and the click/tap picker (touch and mouse tolerance, overlapping-track list); opt-in
  like the one above
- `test_browser_direction.py` — headless-Chromium check of the direction chevrons and
  start/finish markers on a highlighted track; opt-in like the one above
- `test_browser_image_export.py` — headless-Chromium check of saving an image with
  faked tiles: size and zoom, filtered tracks, zoom choices, failed tiles, presets
  (fixed area, zoom, types, dates, line width and map opacity, too-detailed zoom),
  transparent background and "Copy as preset"; opt-in like the one above
- `test_browser_controls.py` — headless-Chromium check of the control layout
  (date panel, tiles/types dropdowns, zoom bar, top-right hamburger) and of the
  tiles select and activity-types multiselect; opt-in like the one above
- `test_browser_date_range.py` — headless-Chromium check of the date-range panel
  (slider, presets, date fields, remembered preset); opt-in like the one above
- `test_leak_guard.py` — the `.githooks` pre-commit guard: realistic synthetic
  Garmin artifacts are rejected and sanitized ones accepted, end-to-end commits in
  a throwaway repo, a whole-repo audit, and (local only, skipped on a fresh clone)
  a check that your real `data/`, `.auth/` and `config-local.toml` are all caught

Fixtures must be synthetic: coordinates within 1° of (0, 0), Garmin owner fields
`null`, no real names, IDs or tokens. The guard enforces this at commit time.

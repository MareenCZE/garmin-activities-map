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

The tests need pytest plus the pipeline's runtime imports. Note that the full
`requirements.txt` currently has an unrelated resolver conflict
(`withings-sync` vs `garth`, from `consolidation.py`, which is outside the map
pipeline), so install the test deps directly:

```bash
pip install pytest folium gpxpy simplification cryptography garminconnect garth
# optional, for coverage:
pip install pytest-cov && python -m pytest --cov=. --cov-report=term-missing
```

## Optional browser test

`test_browser_mapy.py` drives the generated map in headless Chromium to verify
the client-side JavaScript that toggles the Mapy.com attribution logo (the one
thing pure-Python tests can't cover). It **skips automatically** unless Playwright
and a Chromium build are present:

```bash
pip install playwright && playwright install chromium
python -m pytest tests/test_browser_mapy.py
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
- `test_browser_mapy.py` — headless-Chromium check of the Mapy.com logo toggle
  (opt-in; see above)

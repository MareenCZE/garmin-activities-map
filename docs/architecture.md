# Garmin Activities Map — Project Analysis

_Based on reading the source files._

## Purpose

A personal tool (not a polished app) that downloads a user's activities from Garmin
Connect, stores them locally, and renders them as tracks on an interactive Leaflet/Folium
web map. Output can optionally be uploaded to an FTP site for hosting. Comparable in spirit
to StatsHunters, but for Garmin rather than Strava.

## Pipeline

`activities-map.py` is the orchestrator. It reads `config["mode"]` flags and runs up to
four stages, each in its own module:

1. **downloader.py** — pulls new activities from Garmin Connect (via the `garminconnect`
   library), writes per-activity JSON + GPX, and derives simplified coordinate files.
2. **storage.py** — the local "database": a CSV index plus the on-disk file layout.
3. **mapgenerator.py** — builds the HTML map and the per-category JSON data files.
4. **ftpuploader.py** — uploads the HTML + JSON to an FTP server (incremental by default).

There is also a **utility-mode** (separate from the ON/OFF stage flags) for one-off
maintenance ops: `REDOWNLOAD`, `REGENERATE_COORDINATES`, `REGENERATE_CSV`, `RESORT_CSV`,
`ENCRYPT_FTP_PASSWORD`.

`common.py` provides the shared logger, TOML config loading, and Garmin API login. Config
is layered: `config-default.toml` (committed, documented defaults) is overlaid by
`config-local.toml` (git-ignored personal overrides) via a recursive merge.

## Data model & formats

The data lives under `data/` and flows from richest/largest to smallest:

### 1. `data/activities_list.csv` — the master index
One row per activity. This is the "golden source" for map generation.

```
date,time,type,duration,distance,activity_id,name,filename,has_gps_data
2024-01-15,08:00,running,45.0,10.0,0000000000,"Activity name",2024-01-15_0000000000_running,True
```

- `duration` is in **minutes**, `distance` in **km** (converted from Garmin's seconds/metres
  in `downloader.map_to_object`).
- `filename` is the shared stem for that activity's json/gpx/coordinates files, built as
  `{date}_{activity_id}_{type}`.
- `has_gps_data` is a stringified bool (`"True"`/`"False"`).

### 2. `data/json/{stem}.json` — raw Garmin API response
The full, unmodified activity object as returned by Garmin Connect. Kept as a backup and to
allow regenerating the CSV/coordinates without re-downloading. Includes far more than the
map needs (`activityType`, `startTimeLocal`/`startTimeGMT`, `distance`, `duration`,
`averageSpeed`, `calories`, owner info, user roles, etc.). Distances are in metres, durations
in seconds here.

### 3. `data/gpx/{stem}.gpx` — original GPX track
Full-resolution GPS export from Garmin. Not used by the map directly; kept so coordinates can
be re-simplified later at a different precision. Note the README limitation: Garmin refuses
GPX export for very long activities (>~3h).

### 4. `data/coordinates/{stem}.csv` — simplified track
A reduced `latitude,longitude` list, produced from the GPX via the
`simplification` library (Ramer–Douglas–Peucker, epsilon = `coords-simplification-factor`,
default 0.0001) and rounded to `coords-decimal-places` (default 5, ≈1 m). This is what feeds
the map. The count is lower than json/gpx because activities without GPS data have no
coordinate file.

```
latitude,longitude
50.000000,14.000000
...
```

(Fewer coordinate files than GPX/JSON because GPS-less activities produce none.)

## Map generation output

`mapgenerator.create_map_with_activities` produces a **lightweight HTML shell + separate JSON
data files** (a deliberate design for caching and parallel loading, per the recent commit
history):

- Activities are grouped into **categories** (Other, Running, Inline, Skiing, Crosscountry,
  Skimo, Hiking, Cycling), defined by `[activities].mapping` in config — each maps a set of
  Garmin `type_key`s to a display name + colour. Unmapped types fall into the first ("Other")
  category.
- `output/data/{category}_activities.json` — one file per category, an array of minimal
  activity objects: `{coordinates, color, date, name, activity_type, distance, duration,
  activity_id}`. Written compact (no whitespace).
- `output/data/manifest.json` — lists categories (data file, count, colour, `show_on_load`),
  the overall `date_range`, and a `config` block (`enable_highlighting`,
  `enable_area_selection`, `garmin_connect_url`).
- `output/activities_map.html` — a Folium map with empty `FeatureGroup`s per category and a
  `LayerControl`. Folium's generated HTML is then post-processed: noUiSlider CSS/JS is
  injected, the map's JS variable name is discovered by regex, and the JavaScript from
  `templates/activity_loader_template.html` is injected before `</body>`.

### Client-side behaviour (`templates/activity_loader_template.html`)
Pure client JS drives the interactivity:
- Waits for the Folium map + layer control, then robustly maps category names → Leaflet
  layers by parsing the `L.control.layers(...)` base-layer and overlays objects (avoids
  DOM-order fragility). The layer control itself is hidden: a tiles `<select>` and an
  activity-types multiselect dropdown (`initializeLayerSelects`) add/remove the same layers,
  and the hidden control turns that into `overlayadd`/`overlayremove`/`baselayerchange`
  events, which drive lazy loading and resync both dropdowns.
- Lazily fetches each category's JSON (on load if `show_on_load`, otherwise on overlay
  toggle), draws polylines with per-category colour, binds popups (name/date/type/distance/
  duration + Garmin Connect link), and does hover/popup highlighting (bright green).
- A **date-range panel** (`initializeDateRangeSlider`) filters visible tracks by date: a
  noUiSlider, a preset `<select>` (relative ranges plus one entry per year in the data) and two
  native `<input type="date">` fields, kept in sync. It counts whole days as UTC day numbers
  (`isoDateToDay`/`dayToIsoDate`) so timezones and DST can't shift a date; presets are computed
  from the viewer's local "today", clamped to the data's date span, and the last-picked preset
  is kept in `localStorage` (custom ranges are not). The top-left corner stacks the date
  panel and the tiles/types dropdowns under it. The top-right column holds a hamburger
  **toggle control**, the area-select button and the zoom bar (`arrangeTopRightControls`); the
  hamburger shows/hides everything but itself. The button bars share the panels' translucent,
  rounded look.
- An **area-selection tool** (`initializeAreaSelection`, gated by
  `[activities].enable-area-selection`) adds a rectangle-draw button in its own bar between the
  hamburger and the zoom bar (it folds away with the hamburger). The box is drawn from pointer events on the map container, not
  Leaflet's mouse events, because a touch drag fires no `mousedown`/`mousemove`; while armed the
  container gets `touch-action: none`, its `touchstart`/`touchmove` are `preventDefault`ed (iOS
  Safari ignores `touch-action` and would pan the page instead), a "Drag to select an area" hint
  shows, and a second finger
  (a pinch) drops the half-drawn box. Dragging a box lists the activities inside it in a dialog with
  per-category and overall distance/time/count totals, a "partially inside" vs "fully inside"
  toggle, and per-row highlight/popup/Garmin links (a row opens the popup without moving the
  map). It iterates the polylines *currently rendered
  on the map*, so it honours the active date-range and activity-type filters for free, and while
  the box stays up it re-runs the selection live (debounced) when those filters change.
- A **tap picker** (`initializeTapSelection` / `onMapTap`) handles clicks on the map itself
  rather than on the 2 px polylines (their popup click handler is removed). A click picks the
  visible activities whose track passes within `TAP_TOLERANCE_TOUCH_PX` (20) or
  `TAP_TOLERANCE_MOUSE_PX` (6) screen pixels, chosen from the click's `pointerType`. One match
  opens its popup at the click point. Several (overlapping tracks) are listed in the same
  selection dialog the area tool uses, without the partial/full toggle, and the list refreshes
  live when the filters change. The next map click closes that list, whether or not it picks
  anything; a rectangle's list stays until its own close button. Clicks while the area tool is
  armed, and the click that ends a rectangle drag, are ignored.
- A **Mapy.com attribution control** (`initializeMapyAttribution`) adds the clickable
  Mapy.com logo their terms require (30 px, their minimum on-map height), shown only
  while a Mapy.com base layer is active (detected by the active tile layer's URL). The
  copyright link is carried by the tile layer's Leaflet attribution, not repeated here.

### Tile layers & attribution (`mapgenerator.create_map` / `build_tile_layer`)
Base map tiles come from `[map-tiles].tiles` in config. `build_tile_layer` dispatches
per provider:
- **OpenStreetMap** — Folium built-in shorthand (OSM's own tile servers + default OSM
  attribution).
- **CARTO** (`cartodbdark_matter`/`cartodbpositron`/`cartodbvoyager`) — needs a
  `carto-api-key` (watermarked without one, since 2026); built as an explicit keyed URL
  and credited to CARTO + OpenStreetMap with links.
- **Mapy.com** (`mapy.com-*`, formerly Mapy.cz) — needs a `mapy-com-api-key`; skipped
  entirely if absent. Carries the "Seznam.cz a.s. and others" copyright; the logo is
  added client-side (above).

Attribution for each provider is a terms-of-service requirement — the Leaflet attribution
control is left enabled and the strings/logo must not be stripped.

## Notable implementation details

- **Incremental download**: `download_activities` starts from the last stored activity's date
  and skips `activity_id`s already in the CSV. Capped by `max-number-of-activities` (500) to
  avoid hammering Garmin.
- **Incremental FTP upload** (`upload_map_with_data_to_ftp_incremental`): compares local vs
  remote file **size** to decide what to re-upload; `manifest.json` is always uploaded since
  its size rarely changes even when content does. Two other upload variants exist (full, and
  clean-then-full).
- **FTP password** is stored Fernet-encrypted in config. The key is random per machine,
  generated by `ENCRYPT_FTP_PASSWORD` into `.auth/ftp.key` (the token-store dir, git-ignored),
  so a leaked config or repo alone does not reveal the password. `[ftp] protocol` selects
  FTPS (default, `FTP_TLS` + `prot_p`) or plain FTP, which sends credentials in clear text.
  All three upload variants connect through `connect()`. Auth tokens for Garmin persist in
  `.auth/`.
- **Leftover artefacts**: the repo root has a `closure-compiler-*.jar` and `data/` contains
  large `map*.js`/`map.html` files, but minification was disabled/removed per recent commits;
  these appear to be obsolete.

## File-size trade-off (from config comments)
Coordinate simplification epsilon drives output size dramatically for ~2000 activities:
0.001 → 1.8 MB (lossy) · 0.0001 → 11.6 MB (default, good) · unsimplified → 132 MB · raw GPX
→ ~1.2 GB. Coordinate rounding to 5 dp further cuts ~1/3.

## Assessment
Clean, well-commented, single-user tool with a sensible separation of concerns. The staged
CSV-as-database + per-activity file layout makes re-processing cheap and re-download rare. The
main rough edges are the obsolete minification artefacts, plain FTP where a host lacks FTPS, and
size-based FTP change detection (which can miss same-size content changes — mitigated only for
the manifest).

# Architecture

This document describes how Garmin Activities Map is built: the processing pipeline,
the local data store, the generated map and its client-side behaviour, and the upload
step. For installation and everyday use, see the [README](../README.md).

## Overview

The application runs as a batch job. Each run executes up to three stages, and each
stage can be switched on or off independently:

```
Garmin Connect ──► downloader ──► local store (data/) ──► map generator ──► output/ ──► FTP uploader ──► web host
```

| Module              | Responsibility                                                                  |
|---------------------|---------------------------------------------------------------------------------|
| `activities-map.py` | Entry point. Parses the command line, applies it over the config, runs stages.  |
| `common.py`         | Shared logger, TOML config loading, Garmin Connect login.                       |
| `downloader.py`     | Fetches new activities, writes JSON/GPX, derives simplified coordinates.        |
| `storage.py`        | The local store: the CSV index, the `Activity` model and the on-disk layout.    |
| `mapgenerator.py`   | Builds the HTML map, the per-category JSON data files and the manifest.         |
| `ftpuploader.py`    | Uploads the map and its data files over FTPS/FTP; encrypts the FTP password.    |
| `templates/activity_loader_template.html` | All client-side JavaScript and CSS of the map.            |

`consolidation.py` is a standalone set of bulk-maintenance helpers for a Garmin Connect
account (uploading historic GPX/FIT files, re-typing activities). It is not part of the
pipeline and is kept as a reference.

## Configuration

Configuration is TOML, in two layers:

- `config-default.toml` is committed and documents every setting with its default value.
- `config-local.toml` is git-ignored and holds personal values: FTP credentials, tile
  API keys and any overrides.

`common.load_config()` reads the default file and merges the local one over it
recursively, so the local file only needs the keys it changes. The resulting `config`
dictionary is a single shared object that every module imports.

| Section         | Controls                                                                 |
|-----------------|--------------------------------------------------------------------------|
| `[mode]`        | Which stages run (`downloader`, `map-creator`, `uploader`) and the utility mode. |
| `[ftp]`         | Host, user, encrypted password, protocol, remote path and file name.     |
| `[map-tiles]`   | Initial centre and zoom, tile API keys, the list of background maps.     |
| `[activities]`  | Categories and colours, categories shown on load, feature switches, coordinate precision, download cap. |
| `[storage]`     | Paths of the CSV index, the JSON/GPX/coordinate directories and the token store. |
| `[output]`      | Path of the generated HTML file.                                          |

### Command line

Every `[mode]` value can be overridden for a single run, which makes scheduled runs
possible without editing the config:

```
python activities-map.py [--downloader ON|OFF] [--map-creator ON|OFF] [--uploader ON|OFF]
                         [--utility-mode MODE] [--activity-id ID]
```

Options that are not passed keep their configured value.

### Stages and utility modes

`activities-map.run()` executes the enabled stages in a fixed order: download, map
generation, upload. The utility mode then runs a one-off maintenance operation:

| Utility mode              | Effect                                                                  |
|---------------------------|-------------------------------------------------------------------------|
| `REDOWNLOAD`              | Downloads one activity (`activity-id`) again and replaces its files and CSV row. |
| `REGENERATE_COORDINATES`  | Rebuilds every coordinate file from the stored GPX, e.g. after changing the precision settings. |
| `REGENERATE_CSV`          | Rebuilds the CSV index from the stored JSON files.                      |
| `RESORT_CSV`              | Sorts the CSV index by date and time.                                   |
| `ENCRYPT_FTP_PASSWORD`    | Encrypts a plain-text FTP password for the config (see [Upload](#upload)). |

## Download

`downloader.download_new_activities()` logs in through `common.init_api()` and calls
`download_activities()`:

1. The download window starts at the date of the newest stored activity (or 1970 for
   an empty store) and ends now.
2. Garmin Connect is asked for the activities in that window, oldest first. At most
   `max-number-of-activities` (default 500) are processed per run, so the first run of
   a large account is spread over several runs instead of sending a burst of requests.
3. Activities whose ID is already in the CSV index are skipped.
4. For each new activity the downloader stores the raw JSON, downloads the GPX track,
   writes a simplified coordinate file and appends a row to the CSV index.

### Authentication

Login uses the [`garminconnect`](https://github.com/cyberjunky/python-garminconnect)
library. The first run asks for the e-mail, password and, if enabled, an MFA code.
The tokens are then saved in the token store (`.auth/garmin_tokens.json`); later runs
log in from it without prompting, and the library refreshes an expiring token and saves
it back. If the tokens are missing, rejected or in the format of `garminconnect` before
0.3 (`oauth1_token.json`/`oauth2_token.json`, which are no longer read), `init_api()`
falls back to the credential prompt.

## Local store

The `data/` directory is the application's database. All paths are configurable in
`[storage]`. Every activity shares one file name stem, `{date}_{activity_id}_{type}`,
across its JSON, GPX and coordinate files.

### `data/activities_list.csv`: the index

One row per activity. It is the source for map generation.

```
date,time,type,duration,distance,activity_id,name,filename,has_gps_data,elevation_gain,elevation_loss
2024-01-15,08:00,running,45.0,10.0,0000000000,"Activity name",2024-01-15_0000000000_running,True,120,118
```

| Column                              | Meaning                                                        |
|-------------------------------------|----------------------------------------------------------------|
| `date`, `time`                      | Local start date and time.                                     |
| `type`                              | Garmin activity `type_key`, e.g. `running`, `resort_skiing`.   |
| `duration`                          | Minutes (Garmin reports seconds).                              |
| `distance`                          | Kilometres (Garmin reports metres).                            |
| `activity_id`                       | Garmin Connect activity ID.                                    |
| `name`                              | Activity name.                                                 |
| `filename`                          | The shared file name stem.                                     |
| `has_gps_data`                      | `True`/`False`; activities without GPS have no coordinate file. |
| `elevation_gain`, `elevation_loss`  | Total ascent/descent in whole metres; empty when Garmin recorded none. |

An index written before the elevation columns existed is upgraded automatically: the
next download backs it up and rewrites it with the new header, and `REGENERATE_CSV`
fills in the values from the stored JSON.

### `data/json/{stem}.json`: raw activity

The unmodified activity object from Garmin Connect. The map does not need it, but it
allows the CSV to be rebuilt, or other fields to be used later, without downloading
again.

### `data/gpx/{stem}.gpx`: original track

The full-resolution GPS track. It is the input for coordinate files and allows them to
be regenerated with different precision settings.

### `data/coordinates/{stem}.csv`: simplified track

A `latitude,longitude` list derived from the GPX and used by the map:

```
latitude,longitude
0.00012,0.00034
...
```

The track is simplified with the Ramer–Douglas–Peucker algorithm (`simplification`
library, epsilon `coords-simplification-factor`, default 0.0001), and the values are
rounded to `coords-decimal-places` (default 5, about 1 m) when the map is built.

Simplification determines the size of the published data. For a sample of about 2,000
activities:

| Epsilon                | Coordinate data | Quality                     |
|------------------------|-----------------|-----------------------------|
| 0.001                  | 1.8 MB          | Very noticeable loss        |
| 0.0005                 | 3.8 MB          | Noticeable loss             |
| 0.0001 (default)       | 11.6 MB         | Good                        |
| 0.00001                | 41.8 MB         |                             |
| none                   | 132.5 MB        | Original points             |
| (all GPX files)        | 1.2 GB          | Including heart rate etc.   |

Rounding to five decimal places reduces the size by roughly a third.

## Map generation

`mapgenerator.create_map_with_activities()` writes a small HTML page plus separate data
files, so the browser can cache the data and load each category only when it is needed.

### Categories

`[activities].mapping` groups Garmin `type_key`s into display categories, each with a
name and colour (Running, Cycling, Hiking, Skiing, and so on). A type that matches no
category goes into the first one ("Other"). `display-mapping-on-load` lists the
categories that are visible when the page opens; the others load when the viewer turns
them on.

### Output files

| File                                     | Content                                                   |
|------------------------------------------|-----------------------------------------------------------|
| `output/activities_map.html`             | The map page.                                             |
| `output/data/{category}_activities.json` | Compact array of the category's activities.               |
| `output/data/manifest.json`              | Categories, overall date range and feature switches.      |

Each activity in a data file carries `coordinates`, `color`, `date`, `time`, `name`,
`activity_type`, `distance`, `duration` and `activity_id`, plus `elevation_gain` and
`elevation_loss` when they were recorded.

The manifest lists, per category, its data file, activity count, colour and
`show_on_load` flag, and adds the overall `date_range` and a `config` block
(`enable_highlighting`, `enable_area_selection`, `garmin_connect_url`).

### Building the page

1. Folium creates a Leaflet map with the configured background layers, one empty
   `FeatureGroup` per category and a `LayerControl`.
2. The saved HTML is post-processed: the noUiSlider stylesheet and script are added,
   the map's JavaScript variable name is found, and the script from
   `templates/activity_loader_template.html` is inserted before `</body>` with that
   name filled in.

### Background maps and attribution

`[map-tiles].tiles` lists the background maps offered on the page.
`build_tile_layer()` builds each one according to its provider:

| Provider          | Tiles keys                                        | Notes                                              |
|-------------------|---------------------------------------------------|----------------------------------------------------|
| OpenStreetMap     | `OpenStreetMap`                                   | Folium built-in; OSM attribution.                  |
| CARTO             | `cartodbdark_matter`, `cartodbpositron`, `cartodbvoyager` | Needs `carto-api-key` (watermarked without one); credited to CARTO and OpenStreetMap. |
| Mapy.com          | `mapy.com-outdoor`, `mapy.com-winter`; any other `mapy.com-*` key gives the basic map | Needs `mapy-com-api-key`; left out when the key is missing. Credited to "Seznam.cz a.s. and others"; the logo is added on the page. |
| Other             | any [xyzservices](https://xyzservices.readthedocs.io/en/stable/gallery.html) name | Passed to Folium as is, credited to OpenStreetMap contributors. |

The providers' terms require their attribution to stay visible. The Leaflet
attribution control is therefore always enabled, and the attribution strings and the
Mapy.com logo must not be removed. A saved image (see "Saving an image") carries them too.

## Client-side behaviour

All interactivity is plain JavaScript in `templates/activity_loader_template.html`,
running on top of Leaflet.

### Start-up and data loading

The script waits for the Folium map and its layer control, then maps category names to
their Leaflet layers by parsing the `L.control.layers(...)` call rather than relying on
DOM order. It reads the manifest and fetches the data file of every category shown on
load; other categories are fetched the first time they are turned on. Each activity
becomes a polyline in its category colour.

### Controls

- **Layout.** The top-left corner holds the date-range panel with the background and
  activity-type selectors below it, followed by the display-settings button. The top-right
  column holds a menu button, the presets button, the area-selection button, the save-image
  button, the comparison button and the zoom bar (`arrangeTopRightControls`); the menu button hides and shows all
  the other controls and the selection dialog (`placeSelectionDialog`). The presets and save-image panels share a place
  left of the column. The display-settings panel drops down from the tiles/types panel like
  the types menu (`placeDisplaySettingsDialog`). Only one panel is open at a time
  (`closeMapDialogs`).
- **Closing on a tap outside** (`closeOnTapOutside`). The display-settings, presets and
  save-image panels close on a tap or click outside them and their button, and the
  selection on a tap on the map. A press that moves `TAP_SLOP_PX` (8 px) or more, a
  second finger (a pinch), and a press on the zoom bar, an open popup or a selection
  handle are not taps, so the map can be panned and zoomed, and the rectangle resized,
  with a panel open. Only what was open when the press started is closed. A tap on the
  map that closes a panel is swallowed (its click doesn't reach Leaflet), so it doesn't
  also pick a track; one on another control closes the panel and works that control.
  A tap on a track that drops the selection goes on to `onMapTap` (`passTap`) and opens
  that track; one beside the tracks is swallowed too, so a popup opened from the list
  stays. The selection ignores taps on the controls, since its list
  follows their filters.
- **Display settings** (`initializeDisplaySettings`). The gear button opens a dialog
  with four settings, all remembered in `localStorage` (`activitiesMap.displaySettings`).
  *Line width* sets the track width, 1–5 px in 0.5 px steps (default 2 px, opacity 0.8).
  *Thin, see-through lines* draws the tracks at 75 % of that width and 0.35 opacity, so
  at the default width they are 1.5 px. Every place that restores a track after a
  highlight calls `trackStyle(activity)`, so the settings hold after a hover or popup.
  *Map opacity* (20–100 %) sets the opacity of Leaflet's `tilePane` over a white map
  background. That fades every base layer but not the tracks, the Mapy.com logo or the
  attribution. *Show direction* (default on) turns the chevrons and start/finish markers
  of highlighted tracks on or off (`applyShowDirection`). The dialog's controls all go
  through `setDisplaySettings`, like presets do. Below them, *Reset to defaults*
  (`resetMapState`) forgets the remembered state (see "Remembered state") and reloads
  the page. The dialog stays open while the map is moved; the gear, a tap outside it,
  Escape or folding the controls closes it.
- **Background and activity types** (`initializeLayerSelects`). A `<select>` picks the
  background map, and a multi-select dropdown with counts and All/None shortcuts picks
  the categories. Folium's layer control stays on the page, hidden; the two selectors
  drive it (`setBaseLayer`, `setCategoryShown`), so its `baselayerchange`/`overlayadd`/
  `overlayremove` events keep lazy loading and both selectors in sync. The page adds a
  *No map* background (`noMapLayer`, an empty `L.gridLayer`) that the control does not
  list, so `setBaseLayer` fires its `baselayerchange` itself; `applyMapOpacity` gives it
  a white ground.
- **Date range** (`initializeDateRangeSlider`). A noUiSlider, a preset selector and two
  date inputs, kept in sync, filter the visible tracks. Presets cover all time, the last
  30 days, the last 12 months, this and last month, this and last year, and every year
  that has activities. Dates are handled as UTC day numbers (`isoDateToDay`,
  `dayToIsoDate`) so time zones and daylight-saving changes cannot shift them. Presets
  are computed from the viewer's local date and clamped to the data's range. The last
  chosen preset is remembered in `localStorage`, so a relative preset such as "This
  year" follows the calendar; a manually set range is not remembered.

### Activity popup

`createActivityPopupHtml()` renders the popup: the activity name; an icon for the
activity type, the start date and time in the viewer's locale and a link to Garmin
Connect; distance and duration; and total ascent and descent when present. Icons are
Material Symbols (Apache 2.0) inlined as SVG paths, and `ACTIVITY_TYPE_ICONS` maps
Garmin `type_key`s to them.

Hovering over a track, opening its popup or hovering its row in the selection dialog
highlights it (`highlightTrack` / `unhighlightTrack`, style `TRACK_HIGHLIGHT_STYLE`).
While a popup is open, hovering over other tracks does nothing, so the open track stays
the only one highlighted; rows in the selection dialog still highlight on hover.
A highlighted track shows its direction (`showTrackDirection`):

- Grey chevrons every `DIRECTION_CHEVRON_SPACING` (110) screen pixels, pointing the way
  the coordinates were recorded. A chevron is skipped when one pointing the same way is
  already within `DIRECTION_REPEAT_PX` (laps); on an out-and-back both directions show. They are short polylines in their own pane
  (`trackDirectionPane`, above the tracks, `pointer-events: none`) and are rebuilt on
  `zoomend`. They must not share the overlay pane: the hovered track would then no longer
  be its last path, so every `mouseover`'s `bringToFront` would re-append it, the browser
  would fire `mouseover` again, and a click landing in that loop would be lost.
- A start marker (green ▶) and a finish marker (chequered), or one split marker when
  start and finish are within `DIRECTION_LOOP_MAX_GAP` (150 m). They are non-interactive
  `divIcon` markers styled with CSS.

Several tracks can show direction at once (an open popup plus a hovered row in the
selection dialog), so the decorations are kept per track in `trackDirections` and
dropped when a track is removed from the map, or the setting is switched off.

A popup can be dragged
aside by its title (`enablePopupDragging`, based on `L.Draggable`). The drag is stored
in the popup's pixel offset, so the popup keeps its position relative to the track while
the map is panned or zoomed; the popup's tip is hidden once it has been moved. A press
that starts in the popup and ends over the map is not treated as a map click
(`installPopupPressGuard`).

### Selecting tracks by click or tap

Tracks are 2 px wide, which makes them hard to hit, so clicks are handled on the map
itself (`initializeTapSelection`, `onMapTap`) instead of on the polylines. A click
selects the visible activities that pass within `TAP_TOLERANCE_MOUSE_PX` (6 px) of it,
or `TAP_TOLERANCE_TOUCH_PX` (20 px) for a touch, based on the event's `pointerType`.

- One match opens that activity's popup at the click point.
- Several matches (overlapping tracks) are listed in the selection dialog, which is also
  used by the area tool. The list refreshes when the filters change. The next click on
  the map closes it, and picks what it lands on like any other click; a mouse click on
  a row opens that activity and closes the list,
  while a tap on a row leaves it open, since touch screens have no hover to tell the
  tracks apart.
- Clicks while the area tool is active, and the click that ends a rectangle drag, are
  ignored.

### Area selection

`initializeAreaSelection`, enabled by `[activities].enable-area-selection`, adds a
button that arms a rectangle tool. The rectangle is drawn from pointer events on the map
container, so it works with a mouse and with one finger. While the tool is armed the
container uses `touch-action: none` and cancels `touchstart`/`touchmove`, because iOS
Safari ignores `touch-action` and would otherwise scroll the page; a hint is shown, and a
second finger (a pinch) cancels the rectangle.

A finished rectangle gets eight resize handles, on its corners and the middles of its
sides (`addAreaSelectHandles`). They are draggable Leaflet markers, so they work with a
mouse and a finger; a handle moves only its own edges (`resizedAreaBounds`), and
dragging past the opposite edge flips the rectangle. The bounds and the list update
while dragging, and a side handle snaps back to the middle of its side when released.
The handles go with the rectangle when a new one is drawn or the selection is closed,
with its ✕ or a tap on the map.

The resulting dialog lists the activities in the rectangle with totals per category and
overall (count, distance, time), a switch between tracks *partially* and *fully* inside
the rectangle, and per-row highlight, popup and Garmin Connect links. Opening a popup
from a row does not move the map. *Zoom to selection* (`zoomToSelection`, also behind
*Show selection* in the save-image panel) fits the rectangle to the map with
`SELECTION_ZOOM_PADDING_PX` (12 px) around it. It sets `zoomSnap` to 0 for that one
`fitBounds`, so the zoom may stop between whole levels and the rectangle fills the map;
the next zoom by button or wheel snaps back to a whole level. The selection is computed from the polylines currently
on the map, so it follows the date and category filters, and it is recalculated
(debounced) whenever they change while the rectangle is shown, and when a category's
tracks are drawn (a selection restored at start-up comes before the data).

### Saving an image

The camera button (`initializeImageExport`) opens the "Save image" panel, a
`.map-dialog` like the display settings; the selection dialog is hidden while it, the
presets or the display-settings panel is open (`placeSelectionDialog`). It saves the area selection, or the
current view when there is none (`imageExportBounds`; the panel follows the map's
`moveend`). A page cannot screenshot itself, so the area is drawn again on a canvas
(`saveMapImage`, which takes a job from `imageExportJob` of bounds, zoom, base layer,
transparency, map opacity, line scale, file name and tracks).

The zoom is chosen from the current one up to the base map's `maxNativeZoom`
(`imageExportChoices`); a lower zoom already chosen (a preset's `image-zoom`) is offered
too. The tracks are the polylines on the map (`rectangleTracks`, from
`collectVisibleActivities`), so the date and type filters apply, in their SVG paint
order and with their current `options` (display settings, highlight). Highlighted
tracks get chevrons (`directionChevronArms`, shared with `buildDirectionChevrons`) and
start/finish markers (`trackEnds`, drawn to match the CSS markers). *Enlarge lines with
the image* scales lines, markers and the attribution by the zoom factor. The file is
named after the preset whose selection is saved (`presetSelectionName`, dropped when
the selection is redrawn, resized or cleared), else `activities-map-…`.

With *No map* as the base map the job is transparent: the map is left out entirely: no
ground colour, no tiles, and no attribution, as no map is shown. Without tiles to
download, the tile limit and the base map's last zoom do not apply; the zoom list goes
up to `IMAGE_EXPORT_MAX_ZOOM_WITHOUT_MAP` (22) and only the image size limits it.
Otherwise the ground is Leaflet's grey, or white under a faded map, as `applyMapOpacity`
does on screen.

The zoom list is bounded by these limits: more than `IMAGE_EXPORT_MAX_TILES` (400) tiles
(with a map), a side over 16384 px, or over 50 (touch devices: 16) megapixels cannot be
saved. The image is drawn in the map's order: the container background, the tiles for
that zoom at the map opacity (`exportTileUrl` follows `L.TileLayer.getTileUrl`), the
tracks, then the base layer's attribution in the lower-right corner and, on Mapy.com
tiles, the Mapy.com logo above it. Tiles are loaded with `crossOrigin = 'anonymous'` so
the canvas stays readable: OSM and CARTO send `Access-Control-Allow-Origin: *`, Mapy.com
echoes the page's origin (with `Vary: Origin`, so tiles cached for the map are not
reused without it). A tile from a server without CORS fails like one that does not
load; failed tiles stay blank and are counted in the status line, and nothing is saved
when all fail. The PNG is downloaded through an object URL.

### Presets

The bookmark button (`initializePresets`) opens the presets panel. Each preset from
`[[presets]]` is a button showing what it sets (`describePreset`); `applyMapPreset`
applies only the keys the preset has (closing the panel, so the selection dialog shows),
through the same setters as the controls:
`setBaseLayer` (`tiles`), `setDisplaySettings` (`map_opacity`, `line_width`,
`thin_lines`, `show_direction`; saved and shown in the dialog like a change made there),
`setCategoryShown` (`types`), `setDateRange` (`date_range`, set up by the date panel; a
year without data becomes a custom range), `setView` (`center`, `zoom`),
`setAreaSelection` (`selection`, fitted into view when the preset sets no view) and
`imageExportZoom` (`image_zoom`). *New preset from the current state*
(`currentStatePresetToml`) writes the ticked parts (`PRESET_PARTS`) as a `[[presets]]`
entry, copied to the clipboard where allowed.

`mapgenerator.get_presets` checks the presets and puts them into `manifest.json`
(`config.presets`, keys with underscores): a preset without a name, or with nothing
valid to set, is left out; a bad or unknown key is dropped with a warning; a selection
whose image at `image-zoom` is over the limits (`image_size`, computed like the page
does; no tile limit with `tiles = "No map"`) is kept with a warning. A leftover
`[[image-presets]]` section is reported, not converted.

### Remembered state

A reload shows the map as it was left. `currentMapState(parts)` reads the state as plain
data and `applyMapState(state)` sets it through the controls' own setters; the
comparison uses the same pair. Every change reports its part to `onStateChange`: `view`
(`move`/`zoomend`), `tiles` (`baselayerchange`), `types` (`overlayadd`/`overlayremove`),
`display` (`setDisplaySettings`), `selection` (drawn, resized, cleared or its mode
changed) and `fold` (`toggleMapControls`). The parts in `MAP_STATE_PARTS` (view, tiles,
types, selection and its mode) are saved to `localStorage` (`activitiesMap.mapState`),
300 ms after the last change, or on `pagehide` when a save is still waiting. The display
settings and the date preset have their own keys, as above. A hand-picked date range and
the menu fold are not remembered.

At start-up `loadManifest` takes the state handed over by a comparison, else the
remembered one, and downloads first the categories that state shows rather than those
shown on load by the config. Once the controls are set up, `restoreMapState` sets it;
only then are changes saved, so setting up does not overwrite the remembered state.
*Reset to defaults* removes all three keys and reloads the page (in a comparison, the
shell). The second map of a comparison neither reads nor saves any of them.

### Comparison mode

The comparison button (`initializeComparison`) opens the page again as
`activities_map.html?compare`. That page is only a shell (`initializeComparisonShell`):
it removes its own map and shows the page twice, in two iframes of the same origin,
`?pane=primary` and `?pane=secondary` (`COMPARISON_PANE`). They sit side by side, or one
above the other in portrait, at the same size, so the same centre and zoom show the same
area. Each frame is the whole map with its own viewport, so no layout code needed to
change. The second pane hides every control but its date panel, and has no selection
handles. Its selection dialog shows only the summary: the mode switch, close and save
buttons stay on the first map.

The shell keeps the panes in step: everything but the dates. `onStateChange` passes each
change on to the shell (`notifyComparison`), with the parts listed under "Remembered
state". The shell (`onComparisonPaneChange`) reads that part of the pane's state
(`currentMapState`) and sets it on the other pane (`applyMapState`). Changes made while
applying are not reported back (`applyingMapState`), and a view the map already shows is
not set again, so the panes don't echo each other. The functions are
reached directly, as the frames share the shell's origin. Top-level `let` variables are
not properties of `window`, so each pane hands the shell its `state`/`apply` functions in
`announceComparisonPane`.

The dates are passed on only once: when both panes are ready (`onComparisonPaneReady`),
the second takes the first one's whole state, its date range included. The second pane
neither reads nor saves the remembered date preset. A preset applied on the first map
changes its own dates, and its other parts reach the second map as ordinary changes.

The state goes from the single map into the comparison and back through
`sessionStorage` (`handOverComparisonState`, `takeComparisonHandoff`, read once at
start-up in place of the remembered state): opening the comparison passes the single map's state to the first
pane, and closing it passes the first pane's state to the single map.

Each pane loads its own copy of the activity data and draws its own tracks, so a
comparison needs about twice the memory. The second pane's data files and tiles come from
the browser's cache where the servers allow it.

### Mapy.com logo

`initializeMapyAttribution` adds the clickable Mapy.com logo required by the Mapy.com
terms, 30 px high, and shows it only while a Mapy.com background is active (detected
from the active tile layer's URL). The copyright text is part of the tile layer's
Leaflet attribution.

## Upload

`ftpuploader.upload_map_with_data_to_ftp_incremental()` is the upload used by the
pipeline. It uploads the HTML page under the configured remote file name and the
contents of `output/data/`, and skips any file whose remote copy has the same size.
`manifest.json` is always uploaded because its size rarely changes when its content
does. The module also provides a full upload and a variant that clears the remote data
directory first.

Because changes are detected by size only, a data file whose content changes while its
size stays exactly the same is not re-uploaded. A full upload resolves this.

### Connection and credentials

`connect()` opens the connection for every upload variant. `[ftp] protocol` selects
FTPS (the default: `FTP_TLS` with an encrypted data channel) or plain FTP. Plain FTP
sends the login and the files unencrypted and is intended only for hosts without FTPS.

The FTP password is stored in the config encrypted with Fernet. The key is generated
randomly per machine by `ENCRYPT_FTP_PASSWORD` and saved as `ftp.key` in the token
store (`.auth/`), so neither the config nor the repository alone reveals the password.
Without the key file the password has to be encrypted again.

## Testing

The test suite in `tests/` runs with pytest. Pure-Python tests cover the CLI, config
loading, storage, download mapping (with a mocked Garmin API), map and data-file
generation, the upload decisions (with a mocked FTP server) and the pre-commit leak
guard. The `tests/test_browser_*.py` modules build a real map, serve it locally and
drive it in headless Chromium with Playwright; they are the only tests of the
client-side JavaScript. See [tests/README.md](../tests/README.md).

## Repository hygiene

The working copy contains personal data (`data/`, `output/`, `.auth/`,
`config-local.toml`), all of it git-ignored. The pre-commit hook in `.githooks/`
(`leak_guard.py`) additionally rejects commits that contain those paths, GPS tracks,
tokens, credentials, Garmin account fields or precise coordinates. Test fixtures and
documentation use synthetic data only.

`closure-compiler-*.jar` in the repository root is a remnant of a former minification
step and is not used.

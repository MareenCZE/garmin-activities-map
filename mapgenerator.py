#!/usr/bin/env python3
from typing import List
import re
import json
import math
import os
import folium
import folium.plugins

from common import logger, config

# Folium/xyzservices CARTO shorthand -> CARTO raster basemap variant path used in the tile URL
CARTO_TILE_VARIANTS = {
    'cartodbpositron': 'light_all',
    'cartodbdark_matter': 'dark_all',
    'cartodbvoyager': 'rastertiles/voyager',
}


class TypeMapping:
    def __init__(self, name: str, color: str, type_keys: List[str], show_on_load: bool):
        self.name = name
        self.color = color
        self.type_keys = type_keys
        self.show_on_load = show_on_load

    def contains_key(self, type_key):
        return type_key in self.type_keys


uncategorized_activity_types = set()


def get_type_mappings():
    mappings = []
    for mapping in config['activities']['mapping']:
        show_on_load = mapping.get('name') in config['activities']['display-mapping-on-load']
        mappings.append(TypeMapping(mapping.get('name'), mapping.get('color'), mapping.get('type_keys'), show_on_load))
    if not mappings:
        raise ValueError("No type mappings found. Cannot continue. Fix [activities][mapping] config")
    return mappings


def get_type_mapping(mappings: List[TypeMapping], type_key: str) -> TypeMapping:
    for mapping in mappings:
        if mapping.contains_key(type_key):
            return mapping

    if type_key not in uncategorized_activity_types:
        logger.debug(f"Unmapped activity type: {type_key}. Putting it into '{mappings[0].name}' category")
        uncategorized_activity_types.add(type_key)
    return mappings[0]


def calculate_map_center(activities):
    """Calculate the center point of all activities"""
    if not activities:
        return [0, 0]

    total_lat = 0
    total_lon = 0
    count = 0

    for activity in activities:
        if activity.coordinates:
            # Use first coordinate as representative point
            first_coord = activity.coordinates[0]
            if len(first_coord) >= 2:
                total_lat += first_coord[0]  # latitude
                total_lon += first_coord[1]  # longitude
                count += 1

    if count == 0:
        return [0, 0]

    return [total_lat / count, total_lon / count]


def resolve_map_center(activities):
    """Pick the map's opening center.

    Uses the [map-tiles].center-point override from config when set (a
    [latitude, longitude] pair), otherwise falls back to the calculated
    average of all activities.
    """
    configured_center = config['map-tiles'].get('center-point')
    if configured_center:
        return configured_center
    return calculate_map_center(activities)


def create_map(center):
    """Create a Folium map with the tile layers configured in [map-tiles].tiles."""
    activities_map = folium.Map(
        location=center,
        zoom_start=config['map-tiles']['zoom-start'],
        tiles=None
    )

    # Only the first base layer is shown on load; the rest stay selectable in the
    # layer control but aren't added to the map up front. This avoids fetching every
    # provider's tiles on page load and keeps the active-base-layer detection (e.g.
    # for the Mapy.com attribution) accurate.
    shown_a_base_layer = False
    for tile in config['map-tiles']['tiles']:
        layer = build_tile_layer(tile['tiles'], tile['name'])
        if layer is None:
            continue
        layer.show = not shown_a_base_layer
        shown_a_base_layer = True
        layer.add_to(activities_map)
        logger.debug(f"Added tile layer: {tile['name']} (show={layer.show})")

    return activities_map


def build_tile_layer(tile_key, display_name):
    """Resolve one [map-tiles].tiles entry into a folium.TileLayer.

    Returns None when the layer cannot be built (e.g. a keyed provider without a
    configured API key) so the caller can simply skip it.
    """
    if tile_key in CARTO_TILE_VARIANTS:
        return _carto_tile_layer(tile_key, display_name)

    if tile_key.startswith('mapy.com'):
        return _mapy_com_tile_layer(tile_key, display_name)

    if tile_key == 'OpenStreetMap':
        # Built-in Folium tile source - no attribution needed.
        return folium.TileLayer(tiles=tile_key, name=display_name, overlay=False, control=True)

    # Anything else is passed straight through to Folium/xyzservices.
    return folium.TileLayer(tiles=tile_key, name=display_name,
                            attr='© OpenStreetMap contributors', overlay=False, control=True)


def _carto_tile_layer(tile_key, display_name):
    """Build a CARTO basemap layer.

    CARTO raster basemaps require an API key since 2026 - without one the tiles
    come back with an "API KEY REQUIRED" watermark. Folium's shorthand has no
    slot for a key, so build an explicit tile URL when a key is configured and
    otherwise fall back to the (watermarked) shorthand.
    """
    api_key = config['map-tiles'].get('carto-api-key', '')
    if not api_key:
        logger.warning(f"CARTO API key not configured. '{display_name}' tiles will be watermarked. "
                       f"Set carto-api-key in config-local.toml [map-tiles] section.")
        return folium.TileLayer(tiles=tile_key, name=display_name, overlay=False, control=True)

    variant = CARTO_TILE_VARIANTS[tile_key]
    tile_url = f"https://basemaps.cartocdn.com/{variant}/{{z}}/{{x}}/{{y}}.png?key={api_key}"
    # CARTO's terms require crediting both OpenStreetMap and CARTO with links.
    attribution = ('© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, '
                   '© <a href="https://carto.com/attributions">CARTO</a>')
    return folium.TileLayer(tiles=tile_url, name=display_name, attr=attribution,
                            overlay=False, control=True, max_zoom=20)


def _mapy_com_tile_layer(tile_key, display_name):
    """Build a Mapy.com layer, or None when no Mapy.com API key is configured."""
    api_key = config['map-tiles'].get('mapy-com-api-key', '')
    if not api_key:
        logger.warning(f"Mapy.com API key not configured, skipping {display_name}")
        return None

    variant = _mapy_com_variant(tile_key)
    tile_url = f"https://api.mapy.com/v1/maptiles/{variant}/256/{{z}}/{{x}}/{{y}}?apikey={api_key}"
    # Mapy.com requires this exact copyright text with a link. Their logo is a
    # separate visibility requirement handled client-side (initializeMapyAttribution).
    attribution = '© <a href="https://api.mapy.com/copyright">Seznam.cz a.s. and others</a>'
    return folium.TileLayer(tiles=tile_url, name=display_name, attr=attribution,
                            overlay=False, control=True, max_zoom=18)


def _mapy_com_variant(tile_key):
    """Map a 'mapy.com-*' config key to a Mapy.com v1 tileset name (default 'basic')."""
    if 'winter' in tile_key:
        return 'winter'
    if 'outdoor' in tile_key:
        return 'outdoor'
    return 'basic'  # 'mapy.com-base', bare 'mapy.com', or any unrecognized suffix


# The browser's limits for one saved image (IMAGE_EXPORT_* in the template).
IMAGE_EXPORT_MAX_TILES = 400
IMAGE_EXPORT_MAX_SIDE = 16384
IMAGE_EXPORT_MAX_PIXELS = 50_000_000
# Relative date ranges the page knows (DATE_PRESET_OPTIONS in the template), plus 'year-YYYY'.
DATE_RANGE_PRESETS = {'all', 'last-30-days', 'last-12-months', 'this-month', 'last-month', 'this-year', 'last-year'}
ISO_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
# The base map the page adds to the tiles dropdown for drawing the tracks alone (NO_MAP_LAYER_NAME in the template).
NO_MAP_TILES = 'No map'
# The display settings' ranges (LINE_WIDTH_* and MAP_OPACITY_MIN in the template).
LINE_WIDTH_RANGE = (1, 5)
MAP_OPACITY_RANGE = (20, 100)


def _web_mercator_pixels(lat, lon, zoom):
    """World pixel coordinates of a point at a zoom level, for 256 px tiles."""
    scale = 256 * 2 ** zoom
    x = (lon + 180) / 360 * scale
    sin_lat = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


def image_size(bounds, zoom):
    """(width, height, tiles) of the image of bounds saved at zoom, as the page computes it."""
    (south, west), (north, east) = bounds
    x0, y0 = (round(v) for v in _web_mercator_pixels(north, west, zoom))
    x1, y1 = (round(v) for v in _web_mercator_pixels(south, east, zoom))
    tiles = (math.ceil(x1 / 256) - x0 // 256) * (math.ceil(y1 / 256) - y0 // 256)
    return x1 - x0, y1 - y0, tiles


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _valid_date_range(value):
    if isinstance(value, str):
        return value in DATE_RANGE_PRESETS or re.fullmatch(r'year-\d{4}', value) is not None
    return (isinstance(value, list) and len(value) == 2 and all(isinstance(d, str) and ISO_DATE.match(d) for d in value)
            and value[0] <= value[1])


def _valid_center(center):
    return (isinstance(center, list) and len(center) == 2 and all(_is_number(v) for v in center)
            and -85 <= center[0] <= 85 and -180 <= center[1] <= 180)


def _valid_bounds(bounds):
    try:
        (south, west), (north, east) = bounds
    except (TypeError, ValueError):
        return False
    if not all(_is_number(v) for v in (south, west, north, east)):
        return False
    return -85 <= south < north <= 85 and -180 <= west < east <= 180


def _valid_zoom(zoom):
    return _is_number(zoom) and 0 <= zoom <= 22


def _check_types(types, category_names, label):
    if not isinstance(types, list) or not all(isinstance(t, str) for t in types):
        logger.warning(f"{label}: 'types' must be a list of category names; ignoring it")
        return None
    unknown = [t for t in types if t not in category_names]
    if unknown:
        logger.warning(f"{label}: unknown types {unknown} are ignored")
    return [t for t in types if t in category_names]


def get_presets(category_names):
    """The [[presets]] for the page's Presets panel, checked.

    A preset sets part of the map's state: the view (center, zoom), the area
    selection and the detail it is saved as an image at (selection, image-zoom),
    the date range, the activity types, the base map (tiles, incl. "No map")
    and the display settings (map-opacity, line-width, thin-lines,
    show-direction). Every key but 'name' is optional, and the page changes only
    what a preset sets. A bad or unknown key is dropped with a warning; a preset
    without a name, or with nothing left to set, is left out.
    """
    if 'image-presets' in config:
        logger.warning("[[image-presets]] is now [[presets]]: rename it, and in each entry 'bounds' to 'selection' "
                       "and 'zoom' to 'image-zoom'. The old entries are ignored.")
    tile_names = [tile['name'] for tile in config['map-tiles']['tiles']] + [NO_MAP_TILES]
    checks = {
        'center': (_valid_center, "[lat, lon] in degrees"),
        'zoom': (_valid_zoom, "a number from 0 to 22"),
        'selection': (_valid_bounds, "[[south, west], [north, east]] in degrees"),
        'image-zoom': (lambda v: isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 22,
                       "a whole number from 0 to 22"),
        'date-range': (_valid_date_range, f"one of {sorted(DATE_RANGE_PRESETS)}, 'year-YYYY' "
                                          f"or [\"YYYY-MM-DD\", \"YYYY-MM-DD\"]"),
        'tiles': (lambda v: v in tile_names, f"the name of one of [map-tiles].tiles {tile_names}"),
        'map-opacity': (lambda v: _is_number(v) and MAP_OPACITY_RANGE[0] <= v <= MAP_OPACITY_RANGE[1],
                        f"a number from {MAP_OPACITY_RANGE[0]} to {MAP_OPACITY_RANGE[1]} (%); "
                        f"for no map use tiles = \"{NO_MAP_TILES}\""),
        'line-width': (lambda v: _is_number(v) and LINE_WIDTH_RANGE[0] <= v <= LINE_WIDTH_RANGE[1],
                       f"a number from {LINE_WIDTH_RANGE[0]} to {LINE_WIDTH_RANGE[1]} (px)"),
        'thin-lines': (lambda v: isinstance(v, bool), "true or false"),
        'show-direction': (lambda v: isinstance(v, bool), "true or false"),
    }

    presets = []
    for index, raw in enumerate(config.get('presets', [])):
        name = raw.get('name')
        label = f"Preset '{name}'" if name else f"Preset #{index + 1}"
        if not isinstance(name, str) or not name.strip():
            logger.warning(f"{label}: 'name' is missing, skipping it")
            continue
        preset = {'name': name.strip()}
        for key, value in raw.items():
            if key == 'name':
                continue
            if key == 'types':
                types = _check_types(value, category_names, label)
                if types is not None:
                    preset['types'] = types
            elif key not in checks:
                logger.warning(f"{label}: unknown key '{key}' is ignored")
            elif checks[key][0](value):
                preset[key.replace('-', '_')] = value
            else:
                logger.warning(f"{label}: '{key}' must be {checks[key][1]}; ignoring it")
        if len(preset) == 1:
            logger.warning(f"{label}: sets nothing, skipping it")
            continue

        if 'selection' in preset and 'image_zoom' in preset:
            width, height, tiles = image_size(preset['selection'], preset['image_zoom'])
            if preset.get('tiles') == NO_MAP_TILES:
                tiles = 0  # no map: no tiles to download
            if (tiles > IMAGE_EXPORT_MAX_TILES or max(width, height) > IMAGE_EXPORT_MAX_SIDE
                    or width * height > IMAGE_EXPORT_MAX_PIXELS):
                logger.warning(f"{label}: its selection is {width} x {height} px ({tiles} tiles) at image-zoom "
                               f"{preset['image_zoom']}, over the limit of {IMAGE_EXPORT_MAX_TILES} tiles and "
                               f"{IMAGE_EXPORT_MAX_PIXELS // 1_000_000} megapixels; the page will not save it. "
                               f"Lower the image-zoom or shrink the selection.")
        presets.append(preset)
    return presets


def create_activity_data_files(activities, output_dir):
    """Create separate JSON files for each activity category and a manifest"""

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create data directory inside output directory
    data_dir = os.path.join(output_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    # Group activities by category
    mappings = get_type_mappings()
    categories = {}

    for mapping in mappings:
        categories[mapping.name] = {
            'activities': [],
            'color': mapping.color,
            'show_on_load': mapping.show_on_load
        }

    # Process activities
    min_date = None
    max_date = None

    for activity in activities:
        # Use activity_type instead of type_key
        mapping = get_type_mapping(mappings, activity.activity_type)

        # Store minimal activity data - popup HTML will be generated in JavaScript
        activity_data = {
            'coordinates': activity.coordinates,
            'color': mapping.color,
            'date': activity.date,
            'time': activity.time,
            'name': activity.name,
            'activity_type': activity.activity_type,
            'distance': activity.distance,
            'duration': activity.duration,
            'activity_id': activity.activity_id
        }
        # left out when Garmin recorded no elevation; the popup then omits ascent/descent
        if activity.elevation_gain is not None:
            activity_data['elevation_gain'] = activity.elevation_gain
        if activity.elevation_loss is not None:
            activity_data['elevation_loss'] = activity.elevation_loss

        categories[mapping.name]['activities'].append(activity_data)

        # Track date range using activity.date
        activity_date = activity.date
        if min_date is None or activity_date < min_date:
            min_date = activity_date
        if max_date is None or activity_date > max_date:
            max_date = activity_date

    # Create data files for each category
    manifest_categories = {}

    for category_name, category_data in categories.items():
        category_activities = category_data['activities']

        data_file = None
        if category_activities:
            filename = f"{category_name.lower().replace(' ', '_')}_activities.json"
            filepath = os.path.join(data_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(category_activities, f, separators=(',', ':'))

            data_file = f'data/{filename}'

        manifest_categories[category_name] = {
            'data_file': data_file,
            'activity_count': len(category_activities),
            'color': category_data['color'],
            'show_on_load': category_data['show_on_load']
        }

    # Create manifest
    manifest = {
        'categories': manifest_categories,
        'date_range': {
            'min_date': min_date or '1970-01-01',
            'max_date': max_date or '1970-01-01'
        },
        'config': {
            'enable_highlighting': config['activities']['enable-activity-highlighting'],
            'enable_area_selection': config['activities'].get('enable-area-selection', True),
            'garmin_connect_url': config.get('garmin-connect-activity-url', 'https://connect.garmin.com/modern/activity/'),
            'presets': get_presets(list(manifest_categories)),
        }
    }

    manifest_path = os.path.join(data_dir, 'manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        f"Created manifest and {len([c for c in manifest_categories.values() if c['activity_count'] > 0])} category data files in {output_dir}")

    return manifest


def load_activity_loader_template():
    """Load the HTML template containing JavaScript for activity loading"""
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'activity_loader_template.html')

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        logger.debug(f"Template file loaded, length: {len(template_content)} characters")
        logger.debug(f"Template content preview: {template_content[:200]}...")

        # Extract JavaScript from template (between <script> tags)
        script_match = re.search(r'<script>(.*?)</script>', template_content, re.DOTALL)
        if script_match:
            script_content = script_match.group(1).strip()
            logger.debug(f"Extracted JavaScript, length: {len(script_content)} characters")
            logger.debug(f"JavaScript preview: {script_content[:200]}...")
            logger.debug(f"JavaScript ending: ...{script_content[-200:]}")
            return script_content
        else:
            logger.error("No <script> tags found in activity loader template")
            logger.debug(f"Template content: {template_content}")
            return ""

    except FileNotFoundError:
        logger.error(f"Activity loader template not found at: {template_path}")
        logger.error("Please create the templates/activity_loader_template.html file")
        return ""
    except Exception as e:
        logger.error(f"Error loading activity loader template: {e}")
        return ""


def inject_activity_loader_script(html_content, map_var_name):
    """Inject JavaScript to load activities dynamically with date filtering"""

    # Load JavaScript from template
    script_content = load_activity_loader_template()

    if not script_content:
        logger.error("Failed to load activity loader template, map will not have dynamic loading")
        return html_content

    # Replace placeholder with actual map variable name
    script_content = script_content.replace('{{MAP_VAR_NAME}}', map_var_name)
    logger.debug(f"Replaced {{{{MAP_VAR_NAME}}}} with {map_var_name}")

    script = f"""
    <script>
    {script_content}
    </script>
    """

    logger.debug(f"Final script length: {len(script)} characters")
    logger.debug(f"Script preview: {script[:300]}...")

    # Inject script before closing body tag
    html_content = html_content.replace('</body>', script + '\n</body>')
    logger.debug("Script injected into HTML")

    return html_content


def create_map_with_activities(activities, filename):
    output_dir = os.path.dirname(filename)

    # Create activity data files
    manifest = create_activity_data_files(activities, output_dir)

    # Create basic map without activities
    center = resolve_map_center(activities)
    activities_map = create_map(center)

    # Add empty feature groups for ALL categories (not just ones with activities)
    # This ensures JavaScript can find all expected layers
    mappings = get_type_mappings()
    for mapping in mappings:
        # Create FeatureGroup for every category, regardless of activity count
        feature_group = folium.FeatureGroup(
            name=mapping.name,  # This is the key - explicit name for JavaScript
            show=mapping.show_on_load
        )
        feature_group.add_to(activities_map)
        logger.debug(f"Created FeatureGroup for category: {mapping.name} (activity_count: {manifest['categories'][mapping.name]['activity_count']})")

    # Add layer control - this is crucial for JavaScript to find layers. The page
    # hides it and shows its own tiles/types dropdowns, which drive the same layers.
    layer_control = folium.LayerControl(
        collapsed=False,
        position="topleft"
    )
    layer_control.add_to(activities_map)
    logger.debug("Added LayerControl to map")

    # Save the basic map
    activities_map.save(filename)
    logger.debug(f"Saved basic map to {filename}")

    # Read the generated HTML and inject our activity loader
    with open(filename, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Add noUiSlider CSS and JS for date range slider
    nouislider_css = '<link href="https://cdnjs.cloudflare.com/ajax/libs/noUiSlider/15.7.1/nouislider.min.css" rel="stylesheet">'
    nouislider_js = '<script src="https://cdnjs.cloudflare.com/ajax/libs/noUiSlider/15.7.1/nouislider.min.js"></script>'

    # Inject CSS in head
    html_content = html_content.replace('</head>', nouislider_css + '\n</head>')

    # Inject JS before our script
    html_content = html_content.replace('</body>', nouislider_js + '\n</body>')

    # Find the map variable name in the HTML
    map_var_match = re.search(r'var (map_\w+) = L\.map', html_content)
    if map_var_match:
        map_var_name = map_var_match.group(1)
        logger.debug(f"Found map variable name: {map_var_name}")
        # Inject the activity loading script with the correct map variable name
        html_content = inject_activity_loader_script(html_content, map_var_name)
    else:
        logger.error("Could not find map variable name in generated HTML")
        return

    # Write the modified HTML back
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"Created lightweight HTML map ({os.path.getsize(filename) / 1024 / 1024:.1f} MB) with separate data files")
    logger.info(f"Created FeatureGroups for {len(mappings)} categories")

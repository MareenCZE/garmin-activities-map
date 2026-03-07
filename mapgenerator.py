#!/usr/bin/env python3
from typing import List
import re
import json
import os
import folium
import folium.plugins

from common import logger, config


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
    if len(mappings) == 0:
        raise ValueError("No type mappings found. Cannot continue. Fix [map-tiles][tiles] config")
    return mappings


def get_type_mapping(mappings: [], type_key: str) -> TypeMapping:
    for mapping in mappings:
        if mapping.contains_key(type_key):
            return mapping

    if type_key not in uncategorized_activity_types:
        logger.debug(f"Unmapped activity type: {type_key}. Putting it into '{mappings[0]}' category")
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
        if activity.coordinates and len(activity.coordinates) > 0:
            # Use first coordinate as representative point
            first_coord = activity.coordinates[0]
            if len(first_coord) >= 2:
                total_lat += first_coord[0]  # latitude
                total_lon += first_coord[1]  # longitude
                count += 1

    if count == 0:
        return [0, 0]

    return [total_lat / count, total_lon / count]


def create_map(center):
    """Create a basic Folium map"""
    tiles = config['map-tiles']['tiles']

    activities_map = folium.Map(
        location=center,
        zoom_start=config['map-tiles']['zoom-start'],
        tiles=None
    )

    # Add tile layers
    for tile in tiles:
        tile_name = tile['tiles']
        display_name = tile['name']

        # Handle built-in Folium tiles
        if tile_name in ['OpenStreetMap', 'cartodbdark_matter', 'cartodbpositron']:
            logger.debug(f"Adding built-in tile layer: {display_name}")
            folium.TileLayer(
                tiles=tile_name,
                name=display_name,
                overlay=False,
                control=True
            ).add_to(activities_map)

        # Handle custom Mapy.cz tiles
        elif tile_name.startswith('mapy.cz'):
            api_key = config['map-tiles'].get('mapy-cz-api-key', '')
            if api_key:
                logger.debug(f"Adding Mapy.cz tile layer: {display_name}")
                logger.debug(f"Using API key: {api_key[:10]}...{api_key[-4:]}")  # Log partial key for debugging

                # Use correct Mapy.cz API v1 URL format
                if 'winter' in tile_name:
                    tile_url = f"https://api.mapy.cz/v1/maptiles/winter/256/{{z}}/{{x}}/{{y}}?apikey={api_key}"
                elif 'outdoor' in tile_name:
                    tile_url = f"https://api.mapy.cz/v1/maptiles/outdoor/256/{{z}}/{{x}}/{{y}}?apikey={api_key}"
                elif 'base' in tile_name or tile_name == 'mapy.cz':
                    tile_url = f"https://api.mapy.cz/v1/maptiles/basic/256/{{z}}/{{x}}/{{y}}?apikey={api_key}"
                else:
                    # Default to basic map
                    tile_url = f"https://api.mapy.cz/v1/maptiles/basic/256/{{z}}/{{x}}/{{y}}?apikey={api_key}"

                logger.debug(f"Mapy.cz tile URL template: {tile_url.replace(api_key, 'API_KEY_HIDDEN')}")

                try:
                    folium.TileLayer(
                        tiles=tile_url,
                        name=display_name,
                        attr='© Seznam.cz, a.s, © OpenStreetMap',
                        overlay=False,
                        control=True,
                        max_zoom=18
                    ).add_to(activities_map)
                    logger.debug(f"Successfully added Mapy.cz layer: {display_name}")
                except Exception as e:
                    logger.error(f"Error adding Mapy.cz layer {display_name}: {e}")
            else:
                logger.warning(f"Mapy.cz API key not configured, skipping {display_name}")

        # Handle other custom tiles with default attribution
        else:
            logger.debug(f"Adding custom tile layer: {display_name}")
            folium.TileLayer(
                tiles=tile_name,
                name=display_name,
                attr='© OpenStreetMap contributors',
                overlay=False,
                control=True
            ).add_to(activities_map)

    return activities_map


def create_activity_popup_html(activity):
    """Create HTML content for activity popup with clickable Activity ID link and readable duration"""

    # Get Garmin Connect base URL from config
    garmin_base_url = config.get('garmin-connect-activity-url', 'https://connect.garmin.com/modern/activity/')

    # Create clickable link for Activity ID
    activity_link = f'<a href="{garmin_base_url}{activity.activity_id}" target="_blank" style="color: #007cba; text-decoration: none;">{activity.activity_id}</a>'

    # Format duration as "Xh Ymin"
    duration_minutes = int(activity.duration)
    hours = duration_minutes // 60
    minutes = duration_minutes % 60

    if hours > 0:
        duration_formatted = f"{hours}h {minutes}min"
    else:
        duration_formatted = f"{minutes}min"

    popup_html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 12px; line-height: 1.4; max-width: 250px;">
        <div style="font-weight: bold; font-size: 14px; margin-bottom: 8px; color: #333;">
            {activity.name}
        </div>
        <div style="margin-bottom: 4px;">
            <span style="font-weight: bold;">Date:</span> {activity.date}
        </div>
        <div style="margin-bottom: 4px;">
            <span style="font-weight: bold;">Type:</span> {activity.activity_type}
        </div>
        <div style="margin-bottom: 4px;">
            <span style="font-weight: bold;">Distance:</span> {activity.distance} km
        </div>
        <div style="margin-bottom: 4px;">
            <span style="font-weight: bold;">Duration:</span> {duration_formatted}
        </div>
        <div style="margin-bottom: 4px;">
            <span style="font-weight: bold;">Activity ID:</span> {activity_link}
        </div>
    </div>
    """

    return popup_html


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
            'name': activity.name,
            'activity_type': activity.activity_type,
            'distance': activity.distance,
            'duration': activity.duration,
            'activity_id': activity.activity_id
        }

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
        if category_data['activities']:
            filename = f"{category_name.lower().replace(' ', '_')}_activities.json"
            filepath = os.path.join(data_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(category_data['activities'], f, separators=(',', ':'))

            manifest_categories[category_name] = {
                'data_file': f'data/{filename}',
                'activity_count': len(category_data['activities']),
                'color': category_data['color'],
                'show_on_load': category_data['show_on_load']
            }
        else:
            manifest_categories[category_name] = {
                'data_file': None,
                'activity_count': 0,
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
            'garmin_connect_url': config.get('garmin-connect-activity-url', 'https://connect.garmin.com/modern/activity/')
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
    center = calculate_map_center(activities)
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

    # Add layer control - this is crucial for JavaScript to find layers
    layer_control = folium.LayerControl(
        collapsed=False,  # Keep it expanded initially for debugging
        draggable=True,
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

#!/usr/bin/env python3
import logging
import os.path
from typing import List

import folium
import folium.plugins

from storage import load_activities_from_csv, Activity, ACTIVITIES_DATABASE

OUTPUT_MAP_FILENAME = 'data/activities_map.html'
MAPY_CZ_API_KEY_FILENAME = '.auth/mapy_cz_api_key.txt'
ACTIVITY_URL = "https://connect.garmin.com/modern/activity/"


class TypeMapping:
    def __init__(self, name: str, color: str, type_keys: List[str]):
        self.name = name
        self.color = color
        self.type_keys = type_keys

    def contains_key(self, type_key):
        return type_key in self.type_keys


TYPE_MAPPINGS = [TypeMapping("Unknown", 'crimson', []),
                 TypeMapping("Running", 'magenta', ['running', 'track_running', 'trail_running']),
                 TypeMapping('Inline', 'blueviolet', ['inline_skating']),
                 TypeMapping('Skiing', 'red', ['resort_skiing', 'resort_snowboarding', 'resort_skiing_snowboarding_ws']),
                 TypeMapping('Crosscountry', 'dodgerblue', ['skate_skiing_ws', 'cross_country_skiing_ws', 'backcountry_skiing']),
                 TypeMapping('Hiking', 'orangered', ['hiking', 'walking']),
                 TypeMapping('Cycling', 'deeppink', ['cycling', 'mountain_biking', 'gravel_cycling'])]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
uncategorized_activity_types = set()


def get_type_mapping(type_key: str) -> TypeMapping:
    for mapping in TYPE_MAPPINGS:
        if mapping.contains_key(type_key):
            return mapping

    if type_key not in uncategorized_activity_types:
        logger.info("Uncategorized activity type: " + type_key)
        uncategorized_activity_types.add(type_key)
    return TYPE_MAPPINGS[0]


def add_activities_to_map(activities, map):
    activities_count = 0
    feature_groups = {}

    for activity in activities:
        if not activity.has_gps_data:
            logger.debug(f"Skipping due to missing coordinates - {activity}")
            continue
        type_mapping = get_type_mapping(activity.activity_type)
        popup = folium.Popup(create_popup_html(activity), max_width=500)
        feature_group = feature_groups.setdefault(type_mapping.name, folium.FeatureGroup(type_mapping.name))
        folium.PolyLine(activity.coordinates, color=type_mapping.color, weight=3, opacity=0.8,
                                   smooth_factor=3, popup=popup
                                   ).add_to(feature_group)

        # folium.GeoJson(
        #     {
        #         "type": "Feature",
        #         "geometry": {
        #             "type": "LineString",
        #             "coordinates": activity.coordinates
        #         },
        #         "properties": {
        #             "style": {"color": type_mapping.color}
        #         }
        #     },
        #     popup=popup,
        #     style_function=lambda x: x["properties"]["style"],
        #     highlight_function=lambda x: {"color": "lime"},
        #     popup_keep_highlighted=True
        # ).add_to(feature_group)
        # 12.8 MB - using GeoJson with highlighting on mouse hover
        #  8.6 MB - using polylines

        activities_count += 1

    for feature_group in feature_groups.values():
        feature_group.add_to(map)

    logger.info(
        f"Added {activities_count} activities with GPS data divided into {len(feature_groups.keys())} groups to the map")


def create_popup_html(activity: Activity):
    hours, minutes = divmod(activity.duration, 60)
    formatted_duration = f"{int(hours):0}h {int(minutes):0}m"
    type_mapping = get_type_mapping(activity.activity_type)
    return f"{activity.date} {activity.time}<br>{type_mapping.name}<br>{activity.name}<br>{activity.distance} km, {formatted_duration}<br><a href='{ACTIVITY_URL}{activity.activity_id}' target='_blank'>Activity {activity.activity_id}</a>"


def load_mapy_cz_api_key() -> str:
    if os.path.exists(MAPY_CZ_API_KEY_FILENAME):
        with open(MAPY_CZ_API_KEY_FILENAME, 'r') as file:
            return file.read().strip()
    else:
        return None


def create_map():
    # Create a map centered at Prague
    activities_map = folium.Map(location=[50.0755, 14.4378], zoom_start=8, tiles=None)

    # Use Mapy.cz for map tiles, if API key is present.
    # Mapy.cz are in my opinion the best outdoor map for Central Europe region.
    # They however require an API key to work. It is free for usual cases.
    # Visit https://developer.mapy.cz/en/rest-api-mapy-cz/api-key/
    api_key = load_mapy_cz_api_key()
    if api_key:
        folium.TileLayer(
            tiles='https://api.mapy.cz/v1/maptiles/outdoor/256/{z}/{x}/{y}?apikey=' + api_key,
            attr='<a href="https://api.mapy.cz/copyright" target="_blank">© Seznam.cz a.s. a další</a>',
            name='Mapy.cz'
        ).add_to(activities_map)
    else:
        logger.info(
            f"API KEY for Mapy.cz not found. If you want to use Mapy.cz tiles, generate API key and store it in {MAPY_CZ_API_KEY_FILENAME}")

    folium.TileLayer(tiles='OpenStreetMap', name="OSM").add_to(activities_map)
    folium.TileLayer(tiles='cartodbdark_matter', name="Dark").add_to(activities_map)
    folium.TileLayer(tiles='cartodbpositron', name="Light").add_to(activities_map)

    folium.plugins.Fullscreen(
        position="topleft",
        title="Fullscreen",
        title_cancel="Exit",
        force_separate_button=False,
    ).add_to(activities_map)

    folium.plugins.LocateControl(auto_start=False, keepCurrentZoomLevel=True).add_to(activities_map)
    return activities_map


logger.info(f"Reading activities from {ACTIVITIES_DATABASE}")
activities = load_activities_from_csv(ACTIVITIES_DATABASE)
logger.info(f"Found {len(activities)} activities")

activities_map = create_map()
add_activities_to_map(activities, activities_map)
# is it best to add LayerControl as the last item to make it work properly
folium.LayerControl(collapsed=True, draggable=True, position="topleft").add_to(activities_map)

# Save the map to an HTML file
activities_map.save(OUTPUT_MAP_FILENAME)
logger.info(f"Generated {OUTPUT_MAP_FILENAME}. Size: {round(os.path.getsize(OUTPUT_MAP_FILENAME) / 1048576, 1)} MB")
# using jsmin it is possible to reduce size of the file by ˜1 MB

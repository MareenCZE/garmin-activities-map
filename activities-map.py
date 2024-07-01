#!/usr/bin/env python3
import logging
from typing import List

import folium

from storage import load_activities_from_csv, Activity, ACTIVITIES_DATABASE

OUTPUT_MAP_FILENAME = 'data/activities_map.html'

ACTIVITY_URL = "https://connect.garmin.com/modern/activity/"


class TypeMapping:
    def __init__(self, name: str, color: str, type_keys: List[str]):
        self.name = name
        self.color = color
        self.type_keys = type_keys

    def contains_key(self, type_key):
        return type_key in self.type_keys


TYPE_MAPPINGS = [TypeMapping("Unknown", 'red', []),
                 TypeMapping("Running", 'deepskyblue', ['running', 'track_running', 'trail_running']),
                 TypeMapping('Inline', 'limegreen', ['inline_skating']),
                 TypeMapping('Skiing', 'deeppink', ['resort_skiing', 'resort_snowboarding', 'resort_skiing_snowboarding_ws']),
                 TypeMapping('Crosscountry', 'magenta', ['skate_skiing_ws', 'cross_country_skiing_ws', 'backcountry_skiing']),
                 TypeMapping('Hiking', 'yellow', ['hiking', 'walking']),
                 TypeMapping('Cycling', 'darkorange', ['cycling', 'mountain_biking', 'gravel_cycling'])]

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
        polyline = folium.PolyLine(activity.coordinates, color=type_mapping.color, weight=3, opacity=0.8,
                                   smooth_factor=3)
        popup = folium.Popup(create_popup_html(activity), max_width=300)
        polyline.add_child(popup)

        feature_group = feature_groups.setdefault(type_mapping.name, folium.FeatureGroup(type_mapping.name))
        polyline.add_to(feature_group)
        activities_count += 1

    for feature_group in feature_groups.values():
        feature_group.add_to(map)

    logger.info(
        f"Added {activities_count} activities with GPS data divided into {len(feature_groups.keys())} groups to the map")


def create_popup_html(activity: Activity):
    hours, minutes = divmod(activity.duration, 60)
    formatted_duration = f"{int(hours):0}h {int(minutes):0}m"
    type_mapping = get_type_mapping(activity.activity_type)
    return f"{activity.date}<br>{type_mapping.name}<br>{activity.name}<br>{activity.distance} km, {formatted_duration}<br><a href='{ACTIVITY_URL}{activity.activity_id}' target='_blank'>Activity {activity.activity_id}</a>"


logger.info(f"Reading activities from {ACTIVITIES_DATABASE}")
activities = load_activities_from_csv(ACTIVITIES_DATABASE)
logger.info(f"Found {len(activities)} activities")

# Create a map centered at Prague
activities_map = folium.Map(location=[50.0755, 14.4378], zoom_start=8)
folium.TileLayer(tiles='OpenStreetMap').add_to(activities_map)
folium.TileLayer(tiles='OpenTopoMap').add_to(activities_map)
folium.TileLayer(tiles='Esri.WorldTopoMap').add_to(activities_map)
folium.TileLayer(tiles='cartodbpositron').add_to(activities_map)
folium.TileLayer(tiles='cartodbdark_matter').add_to(activities_map)

add_activities_to_map(activities, activities_map)
folium.LayerControl(collapsed=False).add_to(activities_map)

# Save the map to an HTML file
activities_map.save(OUTPUT_MAP_FILENAME)
logger.info(f"Generated {OUTPUT_MAP_FILENAME}")
# using jsmin it is possible to reduce size of the file by ˜1 MB

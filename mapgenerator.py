#!/usr/bin/env python3
import os.path
from typing import List

import folium
import folium.plugins

from common import logger
from storage import Activity

MAPY_CZ_API_KEY_FILENAME = '.auth/mapy_cz_api_key.txt'
ACTIVITY_URL = "https://connect.garmin.com/modern/activity/"


class TypeMapping:
    def __init__(self, name: str, color: str, type_keys: List[str]):
        self.name = name
        self.color = color
        self.type_keys = type_keys

    def contains_key(self, type_key):
        return type_key in self.type_keys


TYPE_MAPPINGS = [TypeMapping("Other", 'grey', []),
                 TypeMapping("Running", 'magenta', ['running', 'track_running', 'trail_running']),
                 TypeMapping('Inline', 'blueviolet', ['inline_skating']),
                 TypeMapping('Skiing', 'red', ['resort_skiing', 'resort_snowboarding', 'resort_skiing_snowboarding_ws']),
                 TypeMapping('Crosscountry', 'dodgerblue', ['skate_skiing_ws', 'cross_country_skiing_ws', 'backcountry_skiing']),
                 TypeMapping('Hiking', 'brown', ['hiking', 'walking']),
                 TypeMapping('Cycling', 'deeppink', ['cycling', 'mountain_biking', 'gravel_cycling'])]

uncategorized_activity_types = set()


def get_type_mapping(type_key: str) -> TypeMapping:
    for mapping in TYPE_MAPPINGS:
        if mapping.contains_key(type_key):
            return mapping

    if type_key not in uncategorized_activity_types:
        logger.debug(f"Unmapped activity type: {type_key}. Putting it into '{TYPE_MAPPINGS[0]}' category")
        uncategorized_activity_types.add(type_key)
    return TYPE_MAPPINGS[0]


def add_activities_to_map(activities, map, enable_highlighting=False):
    activities_count = 0
    feature_groups = {}

    for activity in activities:
        if not activity.has_gps_data:
            logger.debug(f"Skipping due to missing coordinates - {activity}")
            continue
        type_mapping = get_type_mapping(activity.activity_type)
        popup = folium.Popup(create_popup_html(activity), max_width=500)
        feature_group = feature_groups.setdefault(type_mapping.name, folium.FeatureGroup(type_mapping.name))

        # Highlight activity on mouse hover or when selected. Produces a lot of JS code (12.8 MB vs 8.6 MB without it)
        if enable_highlighting:
            folium.GeoJson(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        # GeoJson Features use opposite order of coordinates than Polyline
                        "coordinates": [[point[1], point[0]] for point in activity.coordinates]
                    },
                    "properties": {
                        "style": {"color": type_mapping.color,
                                  # "opacity": 0.8,
                                  # "weight": 3
                                  },
                        # "smoothFactor": 3
                    }
                },
                popup=popup,
                smooth_factor=3,
                style_function=lambda x: x["properties"]["style"],
                # lambda x: {"color": type_mapping.color},
                # lambda x: x["properties"]["style"],
                highlight_function=lambda x: {"color": "lime"},
                popup_keep_highlighted=True
            ).add_to(feature_group)
        else:
            folium.PolyLine(activity.coordinates, color=type_mapping.color, weight=3, opacity=0.8,
                            smooth_factor=3, popup=popup
                            ).add_to(feature_group)

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


def create_map_with_activities(activities, filename, enable_highlighting=False):
    activities_map = create_map()
    add_activities_to_map(activities, activities_map, enable_highlighting)
    # is it best to add LayerControl as the last item to make it work properly
    folium.LayerControl(collapsed=True, draggable=True, position="topleft").add_to(activities_map)

    # Save the map to an HTML file
    activities_map.save(filename)

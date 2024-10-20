#!/usr/bin/env python3
from typing import List

import folium
import folium.plugins

from common import logger, config
from storage import Activity


class TypeMapping:
    def __init__(self, name: str, color: str, type_keys: List[str]):
        self.name = name
        self.color = color
        self.type_keys = type_keys

    def contains_key(self, type_key):
        return type_key in self.type_keys


uncategorized_activity_types = set()


def get_type_mappings():
    mappings = []
    for mapping in config['activities']['mapping']:
        mappings.append(TypeMapping(mapping.get('name'), mapping.get('color'), mapping.get('type_keys')))
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


def add_activities_to_map(activities, map):
    activities_count = 0
    feature_groups = {}
    mappings = get_type_mappings()

    for activity in activities:
        if not activity.has_gps_data:
            logger.debug(f"Skipping due to missing coordinates - {activity}")
            continue
        type_mapping = get_type_mapping(mappings, activity.activity_type)
        popup = folium.Popup(create_popup_html(mappings, activity), max_width=500)
        feature_group = feature_groups.setdefault(type_mapping.name, folium.FeatureGroup(type_mapping.name))

        # Highlight activity on mouse hover or when selected. Produces a lot of JS code (12.8 MB vs 8.6 MB without it)
        if config["activities"]["enable-activity-highlighting"]:
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
                                  }
                    }
                },
                popup=popup,
                smooth_factor=3,
                style_function=lambda x: x["properties"]["style"],
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


def create_popup_html(mappings: [], activity: Activity):
    hours, minutes = divmod(activity.duration, 60)
    formatted_duration = f"{int(hours):0}h {int(minutes):0}m"
    type_mapping = get_type_mapping(mappings, activity.activity_type)
    return f"{activity.date} {activity.time}<br>{type_mapping.name}<br>{activity.name}<br>{activity.distance} km, {formatted_duration}<br><a href='{config['activities']['garmin-connect-activity-url']}{activity.activity_id}' target='_blank'>Activity {activity.activity_id}</a>"


def create_mapy_cz_tiles(name):
    # Use Mapy.cz for map tiles, if API key is present.
    # Mapy.cz are in my opinion the best outdoor map for Central Europe region.
    # They however require an API key to work. It is free for usual cases.
    # Visit https://developer.mapy.cz/en/rest-api-mapy-cz/api-key/
    api_key = config['map-tiles']['mapy-cz-api-key']
    if api_key:
        return folium.TileLayer(
            tiles='https://api.mapy.cz/v1/maptiles/outdoor/256/{z}/{x}/{y}?apikey=' + api_key,
            attr='<a href="https://api.mapy.cz/copyright" target="_blank">© Seznam.cz a.s. a další</a>',
            name=name
        )
    else:
        logger.info(
            f"API KEY for Mapy.cz not found. If you want to use Mapy.cz tiles, generate API key and store it in your config")
        return None


def create_map(center: []):
    activities_map = folium.Map(location=center, zoom_start=config['map-tiles']['zoom-start'], tiles=None)

    for tiles_config in config['map-tiles']['tiles']:
        if tiles_config.get('tiles') == 'mapy.cz':
            mapy_cz_tiles = create_mapy_cz_tiles(tiles_config.get('name'))
            if mapy_cz_tiles:
                mapy_cz_tiles.add_to(activities_map)
        else:
            folium.TileLayer(tiles=tiles_config.get('tiles'), name=tiles_config.get('name')).add_to(activities_map)

    folium.plugins.Fullscreen(
        position="topleft",
        title="Fullscreen",
        title_cancel="Exit",
        force_separate_button=False,
    ).add_to(activities_map)

    folium.plugins.LocateControl(auto_start=False, keepCurrentZoomLevel=True).add_to(activities_map)
    return activities_map


# Calculate center point of activities as an average of their start and end coordinates
def calculate_map_center(activities: [Activity]) -> []:
    center = config['map-tiles']['center-point']
    if not center:
        lat = lon = coord_count = 0
        for activity in activities:
            if activity.coordinates:
                lat += activity.coordinates[0][0] + activity.coordinates[len(activity.coordinates) - 1][0]
                lon += activity.coordinates[0][1] + activity.coordinates[len(activity.coordinates) - 1][1]
                coord_count += 2
        center = [lat / coord_count, lon / coord_count] if coord_count else center
        logger.debug(f"Calculated center point from all activities: {center}")
    return center


def create_map_with_activities(activities, filename):
    center = calculate_map_center(activities)
    activities_map = create_map(center)
    add_activities_to_map(activities, activities_map)
    # is it best to add LayerControl as the last item to make it work properly
    folium.LayerControl(collapsed=True, draggable=True, position="topleft").add_to(activities_map)

    # Save the map to an HTML file
    activities_map.save(filename)

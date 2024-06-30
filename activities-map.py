#!/usr/bin/env python3
import logging
import folium

from storage import load_activities_from_csv, Activity, ACTIVITIES_DATABASE

OUTPUT_MAP_FILENAME = 'data/activities_map.html'

ACTIVITY_URL = "https://connect.garmin.com/modern/activity/"
GROUP_TO_COLOR = {'Running': 'deepskyblue',
                  'Inline': 'limegreen',
                  'Skiing': 'deeppink',
                  'Crosscountry': 'magenta',
                  'Hiking': 'yellow',
                  'Cycling': 'darkorange'
                  }

TYPE_TO_GROUP = {'running': 'Running',
                 'track_running': 'Running',
                 'trail_running': 'Running',
                 'inline_skating': 'Inline',
                 'resort_skiing': 'Skiing',
                 'resort_snowboarding': 'Skiing',
                 'resort_skiing_snowboarding_ws': 'Skiing',
                 'skate_skiing_ws': 'Crosscountry',
                 'cross_country_skiing_ws': 'Crosscountry',
                 'backcountry_skiing': 'Crosscountry',
                 'hiking': 'Hiking',
                 'walking': 'Hiking',
                 'cycling': 'Cycling',
                 'mountain_biking': 'Cycling',
                 'gravel_cycling': 'Cycling'
                 }

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
uncategorized_activity_types = set()


def add_activities_to_map(activities, map):
    activities_count = 0
    groups = {}

    for activity in activities:
        if not activity.has_gps_data:
            logger.debug(f"Skipping due to missing coordinates - {activity}")
            continue
        group_name = TYPE_TO_GROUP.get(activity.activity_type, 'Unknown')
        color = GROUP_TO_COLOR.get(group_name, 'red')
        polyline = folium.PolyLine(activity.coordinates, color=color, weight=3, opacity=0.8, smooth_factor=3)
        popup = folium.Popup(activity.get_popup_html(), max_width=300)
        polyline.add_child(popup)

        group = groups.setdefault(group_name, folium.FeatureGroup(group_name))
        polyline.add_to(group)
        activities_count += 1

    for group in groups.values():
        group.add_to(map)

    logger.info(
        f"Added {activities_count} activities with GPS data divided into {len(groups.keys())} groups to the map")

def create_popup_html(activity:Activity):
    hours, minutes = divmod(activity.duration, 60)
    formatted_duration = f"{int(hours):0}h {int(minutes):0}m"
    type = TYPE_TO_GROUP.get(activity.activity_type, 'Unknown')
    if type == 'Unknown':
        if activity.activity_type not in uncategorized_activity_types:
            logger.info("Uncategorized activity type: " + activity.activity_type)
            uncategorized_activity_types.add(activity.activity_type)
    return f"{activity.date}<br>{type}<br>{activity.name}<br>{activity.distance} km, {formatted_duration}<br><a href='{ACTIVITY_URL}{activity.activity_id}' target='_blank'>Activity {activity.activity_id}</a>"


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

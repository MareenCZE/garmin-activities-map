#!/usr/bin/env python3
import csv
import logging
import folium

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

uncategorized_activity_types = set()
ACTIVITY_URL = "https://connect.garmin.com/modern/activity/"


class Activity:
    def __init__(self, activity_id, distance, duration, date, filename, has_gps_data, activity_type, name):
        self.activity_id = activity_id
        self.link = ACTIVITY_URL + activity_id
        self.distance = float(distance)
        self.duration = float(duration)
        self.date = date
        self.coords_file = f"data/coordinates/{filename}.csv"
        self.has_gps_data = True if has_gps_data == 'Y' else False
        self.activity_type = activity_type
        self.name = name
        self.coordinates = []

    def load_coordinates(self):
        self.coordinates = read_coordinates(self.coords_file)

    def get_popup_tostring(self):
        hours, minutes = divmod(self.duration, 60)
        formatted_duration = f"{int(hours):0}h {int(minutes):0}m"
        type = type_to_group.get(self.activity_type, 'Unknown')
        if type == 'Unknown':
            if self.activity_type not in uncategorized_activity_types:
                logger.info("Uncategorized activity type: " + self.activity_type)
                uncategorized_activity_types.add(self.activity_type)
        return f"{self.date}<br>{type}<br>{self.name}<br>{self.distance} km, {formatted_duration}<br><a href='{self.link}' target='_blank'>Activity {self.activity_id}</a>"


def load_activities_from_csv(csv_filename):
    activities = []
    with open(csv_filename, mode='r', newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            activity = Activity(
                activity_id=row['activity_id'],
                distance=row['distance'],
                duration=row['duration'],
                date=row['date'],
                has_gps_data=row['has_gps_data'],
                filename=row['filename'],
                activity_type=row['type'],
                name=row['name']
            )
            activity.load_coordinates()
            activities.append(activity)

    return activities


def read_coordinates(filename):
    coordinates = []
    with open(filename, mode='r', newline='') as coords_file:
        reader = csv.DictReader(coords_file)
        for row in reader:
            latitude = float(row['latitude'])
            longitude = float(row['longitude'])
            coordinates.append((latitude, longitude))
    return coordinates


def add_activities_to_map(activities, map):
    activities_count = 0
    groups = {}

    for activity in activities:
        if not activity.has_gps_data:
            logger.debug(f"Skipping due to missing coordinates - {activity}")
            continue
        group_name = type_to_group.get(activity.activity_type, 'Unknown')
        color = group_to_color.get(group_name, 'red')
        polyline = folium.PolyLine(activity.coordinates, color=color, weight=3, opacity=0.8, smooth_factor=3)
        popup = folium.Popup(activity.get_popup_tostring, max_width=300)
        polyline.add_child(popup)

        group = groups.setdefault(group_name, folium.FeatureGroup(group_name))
        polyline.add_to(group)
        activities_count += 1

    for group in groups.values():
        group.add_to(map)

    logger.info(
        f"Added {activities_count} activities with GPS data divided into {len(groups.keys())} groups to the map")


group_to_color = {'Running': 'deepskyblue',
                  'Inline': 'limegreen',
                  'Skiing': 'deeppink',
                  'Crosscountry': 'magenta',
                  'Hiking': 'yellow',
                  'Cycling': 'darkorange'
                  }

type_to_group = {'running': 'Running',
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

# Create a map centered at Prague
activities_map = folium.Map(location=[50.0755, 14.4378], zoom_start=8)
folium.TileLayer(tiles='OpenStreetMap').add_to(activities_map)
folium.TileLayer(tiles='OpenTopoMap').add_to(activities_map)
folium.TileLayer(tiles='Esri.WorldTopoMap').add_to(activities_map)
folium.TileLayer(tiles='cartodbpositron').add_to(activities_map)
folium.TileLayer(tiles='cartodbdark_matter').add_to(activities_map)

# Add the GPX track to the map
activities = load_activities_from_csv('data/activities_list.csv')
logger.info(f"Found {len(activities)} activities in the CSV")
add_activities_to_map(activities, activities_map)
folium.LayerControl(collapsed=False).add_to(activities_map)

# Save the map to an HTML file
output_file = '../activities_map-new.html'
activities_map.save(output_file)
logger.info(f"Generated {output_file}")

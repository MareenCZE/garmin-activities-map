import csv
import logging
from datetime import datetime

import folium
import gpxpy
from lxml import etree
from simplification.cutil import simplify_coords

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

uncategorized_activity_types = set()

# Class to hold GPX data
class GPXData:
    def __init__(self, coordinates, duration=0, timestamp="", distance=0):
        self.coordinates = coordinates
        self.duration = duration
        self.timestamp = timestamp
        self.distance = distance

    def __str__(self):
        hours, remainder = divmod(self.duration, 3600)
        minutes, _ = divmod(remainder, 60)
        formatted_duration = f"{int(hours):02}:{int(minutes):02}"
        formatted_distance = round(self.distance / 1000, 1)
        return f"Date: {self.timestamp.date()}<br>Duration: {formatted_duration}<br>Distance: {formatted_distance} km"


# Function to parse GPX file and extract coordinates and duration
def parse_gpx(file_path):
    with open(file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        coordinates = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    coordinates.append((point.latitude, point.longitude))
        # duration = gpx.get_duration()
        # timestamp = gpx.get_time_bounds().start_time
        # distance = gpx.length_2d()
        return GPXData(coordinates)


class TCXData:
    def __init__(self, coordinates, duration, timestamp, distance):
        self.coordinates = coordinates
        self.duration = duration
        self.timestamp = timestamp
        self.distance = distance

    def __str__(self):
        hours, remainder = divmod(self.duration, 3600)
        minutes, _ = divmod(remainder, 60)
        formatted_duration = f"{int(hours):02}:{int(minutes):02}"
        formatted_distance = round(self.distance / 1000, 1)
        return f"Date: {self.timestamp.date()}<br>Duration: {formatted_duration}<br>Distance: {formatted_distance} km"


def parse_tcx(file_path):
    tree = etree.parse(file_path)
    root = tree.getroot()

    ns = {'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

    coordinates = []
    total_distance = 0
    start_time = None
    end_time = None

    for trackpoint in root.xpath('.//tcx:Trackpoint', namespaces=ns):
        time_elem = trackpoint.find('tcx:Time', namespaces=ns)
        if time_elem is not None:
            time = datetime.fromisoformat(time_elem.text.replace('Z', '+00:00'))
            if start_time is None:
                start_time = time
            end_time = time

        pos_elem = trackpoint.find('tcx:Position', namespaces=ns)
        if pos_elem is not None:
            lat_elem = pos_elem.find('tcx:LatitudeDegrees', namespaces=ns)
            lon_elem = pos_elem.find('tcx:LongitudeDegrees', namespaces=ns)
            if lat_elem is not None and lon_elem is not None:
                coordinates.append((float(lat_elem.text), float(lon_elem.text)))

        dist_elem = trackpoint.find('tcx:DistanceMeters', namespaces=ns)
        if dist_elem is not None:
            total_distance = float(dist_elem.text)

    duration = (end_time - start_time).total_seconds() if start_time and end_time else 0
    timestamp = start_time if start_time else datetime.now()

    return TCXData(coordinates, duration, timestamp, total_distance)


class Activity:
    def __init__(self, activity_id, link, distance, duration, date, gpx_file, activity_type, name):
        self.activity_id = activity_id
        self.link = link
        self.distance = float(distance)
        self.duration = float(duration)
        self.date = date
        self.gpx_file = gpx_file
        self.activity_type = activity_type
        self.name = name

    def __str__(self):
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
                link=row['link'],
                distance=row['distance'],
                duration=row['duration'],
                date=row['date'],
                gpx_file=row['gpx-file'],
                activity_type=row['type'],
                name=row['name']
            )
            activities.append(activity)

    return activities


# Parse the GPX file and get the coordinates and duration
# gpx_file_path = '../python-garminconnect/15529274284_ACTIVITY.gpx'
# tcx_file_path = '../python-garminconnect/activity_15946112784.tcx'
# gpx_data = parse_tcx(tcx_file_path)
# parse_gpx(gpx_file_path)

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


# Create a map centered at a specific latitude and longitude
latitude = 50.0755
longitude = 14.4378
activities_map = folium.Map(location=[latitude, longitude], zoom_start=8)
folium.TileLayer(tiles='OpenStreetMap').add_to(activities_map)
#folium.TileLayer(tiles='Stadia.AlidadeSmooth').add_to(folium_map)
#folium.TileLayer(tiles='Stadia.AlidadeSmoothDark').add_to(folium_map)
#folium.TileLayer(tiles='OpenStreetMap.Mapnik').add_to(folium_map)
folium.TileLayer(tiles='OpenTopoMap').add_to(activities_map)
#folium.TileLayer(tiles='Stadia.Outdoors').add_to(folium_map)
#folium.TileLayer(tiles='Thunderforest.Landscape').add_to(folium_map)
#folium.TileLayer(tiles='Esri.WorldStreetMap').add_to(folium_map)
folium.TileLayer(tiles='Esri.WorldTopoMap').add_to(activities_map)
folium.TileLayer(tiles='cartodbpositron').add_to(activities_map)
folium.TileLayer(tiles='cartodbdark_matter').add_to(activities_map)

# heat_map = folium.Map(location=[latitude, longitude], zoom_start=5)
# folium.TileLayer(tiles='OpenStreetMap').add_to(activities_map)
# folium.TileLayer(tiles='OpenTopoMap').add_to(activities_map)
# folium.TileLayer(tiles='Esri.WorldTopoMap').add_to(activities_map)
# folium.TileLayer(tiles='cartodbpositron').add_to(activities_map)
# folium.TileLayer(tiles='cartodbdark_matter').add_to(activities_map)

# Add the GPX track to the map
root_path = '../python-garminconnect/'
activities = load_activities_from_csv(root_path + 'my_activities_list.csv')
logger.info(f"Found {len(activities)} activities")
activities_count = 0
groups = {}
heatmap_coordinates_groups = {}
heatmap_groups = {}

for activity in activities:
    if not activity.gpx_file:
        logger.warning(f"Skipping due to missing GPX data - {activity}")
        continue
    gpx_data = parse_gpx(root_path + activity.gpx_file)
    if len(gpx_data.coordinates) == 0:
        logger.debug(f"Skipping due to empty GPX data - {activity}")
        continue
    group_name = type_to_group.get(activity.activity_type, 'Unknown')
    color = group_to_color.get(group_name, 'red')
    simplified_coordinates = simplify_coords(gpx_data.coordinates, 0.0001)
    #logger.info(f"original coordinates {len(gpx_data.coordinates)} vs simplified {len(simplified_coordinates)}")
    polyline = folium.PolyLine(simplified_coordinates, color=color, weight=3, opacity=0.8, smooth_factor=3)
    popup = folium.Popup(str(activity), max_width=300)
    polyline.add_child(popup)

    group = groups.setdefault(group_name, folium.FeatureGroup(group_name))
    polyline.add_to(group)
    activities_count += 1
    #if activities_count > 100: break

logger.info(f"Added {activities_count} activities with GPS data")
for group in groups.values():
    group.add_to(activities_map)

folium.LayerControl(collapsed=False).add_to(activities_map)
# Save the map to an HTML file
output_file = '../activities_map.html'
activities_map.save(output_file)
logger.info(f"Generated {output_file}")

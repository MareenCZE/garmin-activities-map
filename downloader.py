import csv
import datetime
import json
import os.path
from typing import List

import gpxpy
from garminconnect import Garmin
from simplification.cutil import simplify_coords

import storage
from common import logger, init_api, config


def download_activities(api: Garmin, from_date=None, to_date=None):
    """
    Get activities from GarminConnect within a specified date range and save them to files.
    Appends to a CSV file which is stored as a database of all activities with some basic information about them.
    Exports activity GPS data info into a GPX file.
    Exports other activity fields into a JSON file.
    These two files are not needed for the map but can be used for additional processing without having to re-download
    from Garmin.
    Creates coordinates file from the GPS data by applying a simplification factor to reduce size significantly.

    from_date - optional. Date of last activity in DB is used by default
    to_date - optional. Now used by default
    """

    storage.init_directories()
    existing_activities = storage.load_activities_from_csv(False)

    if not from_date:
        if len(existing_activities) == 0:
            from_date = "1970-01-01"
        else:
            from_date = existing_activities[len(existing_activities) - 1].date
        logger.info(f"From date not specified. Using date from last stored activity: {from_date}")

    api_activities = api.get_activities_by_date(from_date, to_date, None, "asc")

    max_number_of_activities = config["activities"]["max-number-of-activities"]
    if len(api_activities) > max_number_of_activities:
        logger.warn(
            f"Too many activities to process ({len(api_activities)}). Going to process only the first {max_number_of_activities}. Consider using from_date and to_date.")
        api_activities = api_activities[0:max_number_of_activities]

    logger.info(f"Going to process {len(api_activities)} activities")
    processed_activity_ids = get_processed_activity_ids(existing_activities)

    with storage.create_appender() as appender:
        writer = storage.create_writer(appender)
        if len(processed_activity_ids) == 0:
            writer.writeheader()

        for api_activity in api_activities:
            activity_id = api_activity.get('activityId')
            if activity_id in processed_activity_ids:
                logger.info(f"Skipping {activity_id} - already in the CSV, i.e. processed in the past")
                continue

            activity = map_to_object(api_activity)
            save_json_and_gpx(api, activity, api_activity)
            storage.write_activity(writer, activity)


def map_to_object(api_activity):
    activity_id = api_activity.get('activityId')
    time_object = get_datetime_from_activity(api_activity)
    date = time_object.strftime("%Y-%m-%d")
    time = time_object.strftime("%H:%M")
    activity_type = api_activity.get('activityType').get('typeKey') if 'activityType' in api_activity else api_activity.get(
        'activityTypeDTO', {}).get('typeKey', None)
    activity_filename = f"{date}_{activity_id}_{activity_type}"
    distance = api_activity.get('distance') if 'distance' in api_activity else api_activity.get('summaryDTO', {}).get('distance', 0)
    duration = api_activity.get('duration') if 'duration' in api_activity else api_activity.get('summaryDTO', {}).get('duration', 0)

    return storage.Activity(activity_id=activity_id,
                            distance=round(distance / 1000, 2),
                            duration=round(duration / 60, 1),
                            date=date,
                            time=time,
                            filename=activity_filename,
                            has_gps_data=False,
                            activity_type=activity_type,
                            name=api_activity.get('activityName'))


def save_json_and_gpx(api: Garmin, activity: storage.Activity, api_activity):
    logger.info(f"Writing {activity.json_filename}")
    with open(activity.json_filename, 'w') as json_file:
        json.dump(api_activity, json_file)

    gpx_data = api.download_activity(activity.activity_id, dl_fmt=api.ActivityDownloadFormat.GPX)
    if len(gpx_data) > 0:
        coordinates = simplify_coordinates(gpx_data)
        if len(coordinates) > 0:
            logger.info(f"Writing {activity.gpx_filename}")
            with open(activity.gpx_filename, "wb") as gpx_file:
                gpx_file.write(gpx_data)
            activity.coordinates = coordinates
            write_coordinates(activity)
            activity.has_gps_data = True
        else:
            logger.warning(f"No coordinates for {activity.activity_id}")
    else:
        logger.warning(f"No GPS data for {activity.activity_id}")

    return activity


def write_coordinates(activity: storage.Activity):
    logger.info(f"Writing {activity.coords_filename}")
    with open(activity.coords_filename, "w", newline='') as coords_file:
        coords_writer = csv.writer(coords_file)
        coords_writer.writerow(['latitude', 'longitude'])
        coords_writer.writerows(activity.coordinates)


def get_processed_activity_ids(activities: List[storage.Activity]):
    return [activity.activity_id for activity in activities]


def simplify_coordinates(gpx_data):
    gpx = gpxpy.parse(gpx_data)
    coordinates = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                coordinates.append((point.latitude, point.longitude))
    return simplify_coords(coordinates, config["activities"]["coords-simplification-factor"])


def regenerate_simplified_coordinates(activity: storage.Activity):
    with open(activity.gpx_filename, 'r') as gpx_file:
        gpx_data = gpx_file.read()

    activity.coordinates = simplify_coordinates(gpx_data)
    write_coordinates(activity)


# Regenerate all coordinate files from locally stored activity files
#  - To be used e.g. when you change format of the coordinate files or when you experiment with simplification factor
def regenerate_coordinates():
    activities = storage.load_activities_from_csv()
    for activity in activities:
        if activity.has_gps_data:
            regenerate_simplified_coordinates(activity)


def reload_activity(api: Garmin, activity_id):
    logger.info(f"Re-downloading activity {activity_id}")
    api_activity = api.get_activity(activity_id)
    if not api_activity:
        logger.warning(f"No activity {activity_id} found")
        return
    activity = map_to_object(api_activity)
    save_json_and_gpx(api, activity, api_activity)
    storage.update_activity(activity)


def get_datetime_from_activity(activity_json: json):
    if activity_json.get('startTimeLocal'):
        start_time_field = activity_json.get('startTimeLocal')
    else:
        start_time_field = activity_json.get('summaryDTO').get('startTimeLocal')
    return datetime.datetime.fromisoformat(start_time_field)


# Regenerate the CSV file by reading it and writing it again
# - To be used e.g. when you change format of the data or add a column
def regenerate_csv():
    existing_activities = storage.load_and_backup()
    for activity in existing_activities:
        if not os.path.exists(activity.json_filename):
            print(f"{activity.json_filename} does not exist")
            exit(1)
        with open(activity.json_filename, mode='r') as json_file:
            activity_json = json.load(json_file)
        # this piece of code was used to add a time field to the CSV database
        # change it to whatever operation is needed
        time_object = get_datetime_from_activity(activity_json)
        activity.time = time_object.strftime("%H:%M")

    storage.write_database(existing_activities)


# Download recent activities from GarminConnect to update local state to latest
def download_new_activities():
    api = init_api()
    download_activities(api)


# Redownload specific activity (provide activityId below) from GarminConnect and overwrite it locally.
# - To be used when an older activity is modified in GC
def redownload_activity(activity_id):
    api = init_api()
    reload_activity(api, activity_id)

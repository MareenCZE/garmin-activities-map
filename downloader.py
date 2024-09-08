import csv
import datetime
import json
import os.path
from typing import List

import gpxpy
from simplification.cutil import simplify_coords

from common import logger, init_api
from storage import Activity, ACTIVITIES_DATABASE, write_activity, update_activity, init_directories, create_writer, \
    load_activities_from_csv

"""
It is not necessary to use all the full GPS coordinates. They are large and the level of detail is not needed for purposes of the map.
Therefore, using simplification utility to minimize size of the coordinates collection while still keeping almost the same shape of the
route. Size of the coordinates directly affects size of the resulting html file.
The simplification algorithm requires an epsilon parameter. See what impact it had on a sample of my data (˜2000 activities):
0.001    ..   1.8 MB (very noticeable loss of precision)
0.0005   ..   3.8 MB (noticeable loss of precision)
0.0001   ..  11.6 MB (reasonably good)
0.00001  ..  41.8 MB
original .. 132.5 MB (coordinates without simplification)
GPX files..   1.2 GB (all the GPX data, including heartrate etc.)"""
COORDS_SIMPLIFICATION_FACTOR = 0.0001


def download_activities(api, from_date=None, to_date=None):
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

    init_directories()
    csv_filename = ACTIVITIES_DATABASE
    existing_activities = load_activities_from_csv(csv_filename, False)

    if not from_date:
        if len(existing_activities) == 0:
            from_date = "1970-01-01"
        else:
            from_date = existing_activities[len(existing_activities) - 1].date
        logger.info(f"From date not specified. Using {from_date}")

    api_activities = api.get_activities_by_date(from_date, to_date, None, "asc")

    if len(api_activities) > 500:
        logger.warn(
            f"Too many activities to process ({len(api_activities)}). Going to process only the first 500. Consider using from_date and to_date.")
        api_activities = api_activities[0:500]

    logger.info(f"Going to process {len(api_activities)} activities")
    processed_activity_ids = get_processed_activity_ids(existing_activities)

    logger.info(f"Output going into {csv_filename}")
    with open(csv_filename, mode='a', newline='') as csv_file:
        writer = create_writer(csv_file)
        if len(processed_activity_ids) == 0:
            writer.writeheader()

        for api_activity in api_activities:
            activity_id = api_activity.get('activityId')
            if activity_id in processed_activity_ids:
                logger.info(f"Skipping {activity_id} - already in the CSV, i.e. processed in the past")
                continue

            activity = map_to_object(api_activity)
            save_json_and_gpx(activity, api_activity)
            write_activity(writer, activity)


def map_to_object(api_activity):
    activity_id = api_activity.get('activityId')
    time_object = datetime.datetime.fromisoformat(api_activity.get('startTimeLocal'))
    date = time_object.strftime("%Y-%m-%d")
    time = time_object.strftime("%H:%M")
    activity_type = api_activity.get('activityType', {}).get('typeKey')
    activity_filename = f"{date}_{activity_id}_{activity_type}"

    return Activity(activity_id=activity_id,
                    distance=round(api_activity.get('distance') / 1000, 2) if api_activity.get('distance') else 0,
                    duration=round(api_activity.get('duration') / 60, 1),
                    date=date,
                    time=time,
                    filename=activity_filename,
                    has_gps_data=False,
                    activity_type=activity_type,
                    name=api_activity.get('activityName'))


def save_json_and_gpx(activity: Activity, api_activity):
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


def write_coordinates(activity: Activity):
    logger.info(f"Writing {activity.coords_filename}")
    with open(activity.coords_filename, "w", newline='') as coords_file:
        coords_writer = csv.writer(coords_file)
        coords_writer.writerow(['latitude', 'longitude'])
        coords_writer.writerows(activity.coordinates)


def get_processed_activity_ids(activities: List[Activity]):
    return [activity.activity_id for activity in activities]


def simplify_coordinates(gpx_data):
    gpx = gpxpy.parse(gpx_data)
    coordinates = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                coordinates.append((point.latitude, point.longitude))
    return simplify_coords(coordinates, COORDS_SIMPLIFICATION_FACTOR)


def regenerate_simplified_coordinates(activity: Activity):
    with open(activity.gpx_filename, 'r') as gpx_file:
        gpx_data = gpx_file.read()

    activity.coordinates = simplify_coordinates(gpx_data)
    write_coordinates(activity)


def regenerate_coordinates():
    activities = load_activities_from_csv(ACTIVITIES_DATABASE)
    for activity in activities:
        if activity.has_gps_data:
            regenerate_simplified_coordinates(activity)


def reload_activity(api, activity_id):
    logger.info(f"Re-downloading activity {activity_id}")
    api_activity = api.get_activity(activity_id)
    if not api_activity:
        logger.warning(f"No activity {activity_id} found")
        return
    activity = map_to_object(api_activity)
    save_json_and_gpx(activity, api_activity)
    update_activity(activity)


def regenerate_csv():
    csv_filename = ACTIVITIES_DATABASE
    existing_activities = load_activities_from_csv(csv_filename, False)
    for activity in existing_activities:
        if not os.path.exists(activity.json_filename):
            print(f"{activity.json_filename} does not exist")
            exit(1)
        with open(activity.json_filename, mode='r') as json_file:
            activity_json = json.load(json_file)
        # this piece of code was used to add a time field to the CSV database
        # change it to whatever operation is needed
        if activity_json.get('startTimeLocal'):
            start_time_field = activity_json.get('startTimeLocal')
        else:
            start_time_field = activity_json.get('summaryDTO').get('startTimeLocal')
        time_object = datetime.datetime.fromisoformat(start_time_field)
        activity.time = time_object.strftime("%H:%M")

    new_filename = csv_filename + datetime.datetime.now().strftime("%y%m%d%H%M%s")
    logger.info(f"Saving back up of the original database as {new_filename}")
    os.rename(csv_filename, new_filename)
    with open(csv_filename, mode='w', newline='') as csv_file:
        writer = create_writer(csv_file)
        writer.writeheader()

        for activity in existing_activities:
            write_activity(writer, activity)

        logger.info(f"Created {csv_file.name} with {len(existing_activities)} activities")


# ##########################################################
# Main program
# ##########################################################

# Choose mode of operation
#   DOWNLOAD
#       - Download recent activities from GarminConnect to update local state to latest
#   REDOWNLOAD
#       - Download specific activity (provide activityId below) from GarminConnect and overwrite it locally.
#       - To be used when an older activity is modified in GC
#   REGENERATE_COORDINATES
#       - Regenerate all coordinate files from locally stored activity files
#       - To be used e.g. when you change format of the coordinate files or when you experiment with simplification factor
#   REGENERATE_CSV
#       - Regenerate the CSV file by reading it and writing it again
#       - To be used e.g. when you change format of the data or add a column
mode = "DOWNLOAD"
activity_id = None    # only relevant for REDOWNLOAD mode, e.g. 1700000403

if mode == "DOWNLOAD":
    api = init_api()
    download_activities(api)
elif mode == "REDOWNLOAD":
    api = init_api()
    reload_activity(api, activity_id)
elif mode == "REGENERATE_COORDINATES":
    regenerate_coordinates()
elif mode == "REGENERATE_CSV":
    regenerate_csv()

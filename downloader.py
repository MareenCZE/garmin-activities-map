import csv
import datetime
import json
import os

import gpxpy
from simplification.cutil import simplify_coords

from common import logger, init_api

COORDS_SIMPLIFICATION_FACTOR = 0.0001


def download_activities(api, from_date, to_date=None):
    """
    Get activities from GarminConnect within a specified date range and save them to files.
    Appends to a CSV file which is stored as a database of all activities with some basic information about them.
    Exports activity GPS data info into a GPX file.
    Exports other activity fields into a JSON file.
    These two files are not needed for the map but can be used for additional processing without having to re-download
    from Garmin.
    Creates coordinates file from the GPS data by applying a simplification factor to reduce size significantly.
    """

    os.makedirs('data/json', exist_ok=True)
    os.makedirs('data/gpx', exist_ok=True)
    os.makedirs('data/coordinates', exist_ok=True)
    csv_filename = 'data/activities_list.csv'

    activities = api.get_activities_by_date(from_date, to_date, None, "asc")
    logger.info(f"Going to process {len(activities)} activities")
    processed_activity_ids = get_processed_activity_ids(csv_filename)

    fieldnames = ['date', 'type', 'duration', 'distance', 'activity_id', 'name', 'filename', 'has_gps_data']

    logger.info(f"Output going into {csv_filename}")
    with open(csv_filename, mode='a', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if len(processed_activity_ids) == 0:
            writer.writeheader()

        for activity in activities:
            activity_id = activity.get('activityId')
            if str(activity_id) in processed_activity_ids:
                logger.info(f"Skipping {activity_id} - already in the CSV, i.e. processed in the past")
                continue

            date = datetime.datetime.fromisoformat(activity.get('startTimeLocal')).strftime("%Y-%m-%d")
            activity_type = activity.get('activityType', {}).get('typeKey')
            activity_filename = f"{date}_{activity_id}_{activity_type}"
            json_filename = f"data/json/{activity_filename}.json"
            gpx_filename = f"data/gpx/{activity_filename}.gpx"
            coordinates_filename = f"data/coordinates/{activity_filename}.csv"

            logger.info(f"Writing {json_filename}")
            with open(json_filename, 'w') as json_file:
                json.dump(activity, json_file)

            gpx_data = api.download_activity(activity_id, dl_fmt=api.ActivityDownloadFormat.GPX)
            has_gps_data = False
            if len(gpx_data) > 0:
                coordinates = simplify_coordinates(gpx_data)
                if len(coordinates) > 0:
                    logger.info(f"Writing {gpx_filename}")
                    with open(gpx_filename, "wb") as gpx_file:
                        gpx_file.write(gpx_data)
                    logger.info(f"Writing {coordinates_filename}")
                    with open(coordinates_filename, "w", newline='') as coords_file:
                        coords_writer = csv.writer(coords_file)
                        coords_writer.writerow(['latitude', 'longitude'])
                        coords_writer.writerows(coordinates)
                    has_gps_data = True
                else:
                    logger.warning(f"No coordinates for {activity_id}")
            else:
                logger.warning(f"No GPS data for {activity_id}")

            writer.writerow(
                {'name': activity.get('activityName'),
                 'activity_id': activity_id,
                 'type': activity_type,
                 'date': date,
                 'duration': round(activity.get('duration') / 60, 1),
                 'distance': round(activity.get('distance') / 1000, 2) if activity.get('distance') else 0,
                 'filename': activity_filename,
                 'has_gps_data': str('Y' if has_gps_data else 'N')})


def get_processed_activity_ids(csv_filename):
    activity_ids = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, mode='r', newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                activity_ids.add(row['activity_id'])

    return activity_ids


def simplify_coordinates(gpx_data):
    gpx = gpxpy.parse(gpx_data)
    coordinates = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                coordinates.append((point.latitude, point.longitude))
    return simplify_coords(coordinates, COORDS_SIMPLIFICATION_FACTOR)


# Main program
api = init_api()
download_activities(api, "2024-06-23")

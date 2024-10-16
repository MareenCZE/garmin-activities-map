import csv
import datetime
import os
import shutil
from typing import List

from common import logger, config


def init_directories():
    activities_config = config['storage']
    os.makedirs(activities_config['directory-json'], exist_ok=True)
    os.makedirs(activities_config['directory-gpx'], exist_ok=True)
    os.makedirs(activities_config['directory-coordinates'], exist_ok=True)


class Activity:
    def __init__(self, activity_id, distance, duration, date, time, filename, has_gps_data, activity_type, name):
        self.activity_id = activity_id
        self.distance = float(distance)
        self.duration = float(duration)
        self.date = date
        self.time = time
        self.filename = filename
        activities_config = config['storage']
        self.coords_filename = f"{activities_config['directory-coordinates']}/{filename}.csv"
        self.json_filename = f"{activities_config['directory-json']}/{filename}.json"
        self.gpx_filename = f"{activities_config['directory-gpx']}/{filename}.gpx"
        self.has_gps_data = has_gps_data
        self.activity_type = activity_type
        self.name = name
        self.coordinates = []

    def load_coordinates(self):
        if self.has_gps_data:
            self.coordinates = read_coordinates(self.coords_filename)

    def __str__(self):
        return f"Activity({self.activity_id}, {self.date} {self.time}, {self.name})"


def load_activities_from_csv(load_coordinates=True):
    activities = []
    csv_filename = config['storage']['activities-database']
    logger.info(f"Reading activities from {csv_filename}")
    with open(csv_filename, mode='r', newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            activity = Activity(
                activity_id=int(row['activity_id']),
                distance=float(row['distance']),
                duration=float(row['duration']),
                date=row['date'],
                time=row['time'],
                has_gps_data=True if row['has_gps_data'] == 'True' else False,
                filename=row['filename'],
                activity_type=row['type'],
                name=row['name']
            )
            if load_coordinates:
                activity.load_coordinates()
            activities.append(activity)

    return activities


def read_coordinates(filename):
    coordinates = []
    with open(filename, mode='r', newline='') as coords_file:
        reader = csv.DictReader(coords_file)
        for row in reader:
            latitude = round(float(row['latitude']), config['activities']['coords-decimal-places'])
            longitude = round(float(row['longitude']), config['activities']['coords-decimal-places'])
            coordinates.append([latitude, longitude])
    return coordinates


def write_database(activities: List[Activity], filename=config['storage']['activities-database']):
    logger.info(f"Writing into {filename}")
    with open(filename, mode='w', newline='') as csv_file:
        writer = create_writer(csv_file)
        writer.writeheader()
        for activity in activities:
            write_activity(writer, activity)


def write_activity(writer, activity: Activity):
    writer.writerow(
        {'name': activity.name,
         'activity_id': activity.activity_id,
         'type': activity.activity_type,
         'date': activity.date,
         'time': activity.time,
         'duration': activity.duration,
         'distance': activity.distance,
         'filename': activity.filename,
         'has_gps_data': str(activity.has_gps_data)})


def create_appender(filename=config['storage']['activities-database']):
    logger.info(f"Output going into {filename}")
    return open(filename, mode='a', newline='')


def create_writer(file_handler):
    fieldnames = ['date', 'time', 'type', 'duration', 'distance', 'activity_id', 'name', 'filename', 'has_gps_data']
    return csv.DictWriter(file_handler, fieldnames=fieldnames)


def load_and_backup():
    # create a backup
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    backup_filename = f"{config['storage']['activities-database']}.{timestamp}"
    logger.info(f"Creating a backup - {backup_filename}")
    shutil.copy2(config['storage']['activities-database'], backup_filename)

    activities = load_activities_from_csv(False)
    logger.info(f"Loaded {len(activities)} activities")
    return activities


def resort_database():
    logger.info("Re-sorting the database")
    activities = load_and_backup()
    sorted_activities = sorted(activities, key=lambda activity: (activity.date, activity.activity_id))
    write_database(sorted_activities, config['storage']['activities-database'])


def delete_activity(activity_id):
    logger.info(f"Deleting activity {activity_id}")
    activities = load_and_backup()
    activity = next((activity for activity in activities if activity.activity_id == activity_id), None)

    if not activity:
        logger.warning(f"Activity not found in the database. Nothing deleted")
        return

    activities.remove(activity)
    delete_activity_files(activity)
    write_database(activities, config['storage']['activities-database'])


def delete_activity_files(activity: Activity):
    if os.path.exists(activity.coords_filename):
        logger.info(f"Deleting {activity.coords_filename}")
        os.remove(activity.coords_filename)
    if os.path.exists(activity.gpx_filename):
        logger.info(f"Deleting {activity.gpx_filename}")
        os.remove(activity.gpx_filename)
    if os.path.exists(activity.json_filename):
        logger.info(f"Deleting {activity.json_filename}")
        os.remove(activity.json_filename)


def update_activity(new_activity: Activity):
    activities = load_and_backup()
    old_activity = next((activity for activity in activities if activity.activity_id == new_activity.activity_id), None)

    if not old_activity:
        logger.warning(f"Activity not found in the database. Nothing to be updated")
        return

    # date and type are part of filename, if they differ, the old files need to be deleted
    if old_activity.date != new_activity.date or old_activity.activity_type != new_activity.activity_type:
        delete_activity_files(old_activity)

    # replace the activity with the new version and save the DB
    # it is not expected that date of the activity would change. If it does, make sure to re-sort the DB
    logger.info(f"Replacing {str(old_activity)} with {str(new_activity)}")
    index = activities.index(old_activity)
    activities[index] = new_activity
    write_database(activities, config['storage']['activities-database'])

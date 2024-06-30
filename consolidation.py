#!/usr/bin/env python3
"""
This is not really useful or meant for general use. Keeping it here for inspiration if someone wants to do something
similar I went through.

Functions to do various bulk operations with Garmin activities. The idea was to get my GarminConnect account
up to date with my sport activities records. I had my own offline records of my past sport activities and
wanted to convey that information in GarminConnect consistently.
I used these functions to upload activities for which I had GPX or FIT files locally. Scripts were helping to avoid
uploading duplicates. They also took care of splitting the files first if they contained multiple segments which
does not work correctly in GarminConnect.
I also used these to export existing activities and to categorize them correctly based on some decision logic. This
was needed because large number of activities had incorrect activity type simply because true types (e.g. inline skating)
were not available on my device back then.
I also used these to upload manual activities in cases where I only had some basic stats about the activity without
any GPS data.
"""

import csv
import datetime
import json
import time
import xml.etree.ElementTree as ET

from common import logger, init_api

#
# GARMIN ACTIVITY TYPES
#
# Mapping a user-friendly name to a list of Garmin constants (type_id, type_key, parent_type_id).
# To be used when changing type of activity
# Subset used by me, check existing activities or use following links to get values for other types
#   https://connect.garmin.com/modern/main/js/properties/activity_types/activity_types.properties
#   https://connect.garmin.com/modern/main/js/properties/event_types/event_types.properties
ACTIVITY_TYPES = {'running': [1, "running", 17],
                  'inline': [63, "inline_skating", 4],
                  'skiing': [251, "resort_skiing", 165],
                  'snowboarding': [252, "resort_snowboarding", 165],
                  'skiingSnowboarding': [172, "resort_skiing_snowboarding_ws", 165],
                  'crossCountry': [170, "skate_skiing_ws", 165],
                  'crossCountryClassic': [171, "cross_country_skiing_ws", 165],
                  'backcountry': [203, "backcountry_skiing", 165],
                  'hiking': [3, "hiking", 17],
                  'cycling': [2, "cycling", 17]}


# ###################
# HELPER FUNCTIONS
# ###################
def display_json(api_call, output):
    """Format API output for better readability."""

    dashed = "-" * 20
    header = f"{dashed} {api_call} {dashed}"
    footer = "-" * len(header)

    print(header)

    if isinstance(output, (int, str, dict, list)):
        print(json.dumps(output, indent=4))
    else:
        print(output)

    print(footer)


def activity_tostring(activity):
    """Get a shorter toString representation of an activity"""
    return f"{activity.get('activityId')}, {activity.get('activityName')}, {activity.get('startTimeGMT')}, typeId={activity.get('activityType').get('typeId')}, typeKey={activity.get('activityType').get('typeKey')}, parentTypeId={activity.get('activityType').get('parentTypeId')}, distance={round(activity.get('distance') / 1000, 1)}, duration={round(activity.get('duration') / 60, 0)}, avgSpeed={round(activity.get('averageSpeed') * 3.6, 1)},"


# ###################
# MAIN LOGIC
# ###################
def get_activity_by_id(api, activity_id):
    """ Get activity by ID and print it out as JSON. Useful to see names of all the fields available on an activity."""

    display_json(
        f"api.get_activity({activity_id})",
        api.get_activity(activity_id),
    )


def categorize_activities(api):
    """
    Export a list of activities from GarminConnect and determine their true activity type based on some basic decision rules

    This was used to clean up state in GarminConnect. I had a number of activities there which were not done by me.
    Furthermore, there were duplicate activities (e.g. from comparing device precision by using multiple devices at
    the same time, duplicate uploads of the same activity, uploads of the same activity from my device as well as from
    my wife's).

    STEPS
     - Get activities from GarminConnect
     - Classify the activity based on some basic logic (see DECISION LOGIC below and ACTIVITY_TYPES above)
     - Write basic parameters of the activities along with their calculated types into a CSV to allow further processing
    """

    # INPUT PARAMETERS
    start_date = datetime.date(2014, 1, 1)
    end_date = datetime.date(2014, 6, 30)
    activity_type = None  # type of activities in GarminConnect to process
    # ################

    activities = api.get_activities_by_date(start_date, end_date, activity_type, "asc")

    if not activities:
        print("No activities found")
        return

    logger.info("Processing " + str(len(activities)) + " activities")
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"data/activities_{timestamp}.csv"
    logger.info("Writing output into " + output_file)

    with open(output_file, "w", newline="") as csv_file:
        writer = csv.writer(csv_file, dialect="excel", delimiter=';', quoting=csv.QUOTE_NONE)
        writer.writerow(
            ["ActivityId", "StartTimeLocal", "ActivityName", "Distance", "AverageSpeed", "MaxSpeed", "ElevationGain",
             "ElevationLoss", "TypeId", "TypeKey", "ParentTypeId", "NewType"])

        for activity in activities:
            logger.info(str(activity))
            activity_name = activity.get("activityName") if activity.get("activityName") else ""
            start_time_local = activity.get("startTimeLocal")
            distance = round(activity.get("distance") / 1000, 1)
            average_speed = round(activity.get("averageSpeed") * 3.6, 1)
            max_speed = round(activity.get("maxSpeed") * 3.6, 1)
            elevation_gain = round(activity.get("elevationGain"), 1) if activity.get("elevationGain") else 0
            elevation_loss = round(activity.get("elevationLoss"), 1) if activity.get("elevationLoss") else 0
            new_type = "KEEP"
            month = datetime.datetime.fromisoformat(start_time_local).month

            # DECISION LOGIC - generally not useful, very specific to myself
            if "Praha 2-Nusle" in activity_name:
                new_type = "KEEP"
            elif (month in [1, 2, 3, 12] and (
                    "Mariánské Hory" in activity_name or "Jizerka" in activity_name or "Kořenov" in activity_name)):
                new_type = "crossCountry"
            elif "Račice" in activity_name or "Opava" in activity_name or "Dolní Počernice" in activity_name or "Jaktař" in activity_name or "Židlochovice" in activity_name or "Ostrava" in activity_name or "Kateřinky" in activity_name or "Hrotovice" in activity_name:
                new_type = "inline"
            elif elevation_gain > 1200:
                new_type = "skiing"
            elif distance > 15 or average_speed > 14 or max_speed > 20 or average_speed < 6:
                new_type = "???"

            # ###################
            writer.writerow(
                [activity.get("activityId"), start_time_local, activity_name, str(distance).replace('.', ','),
                 str(average_speed).replace('.', ','), str(max_speed).replace('.', ','),
                 str(elevation_gain).replace('.', ','), str(elevation_loss).replace('.', ','),
                 activity.get("activityType").get("typeId"), activity.get("activityType").get("typeKey"),
                 activity.get("activityType").get("parentTypeId"), new_type])

    return None


def update_activity_type(api):
    """
    Process a list of activities from a file and change their type or delete them from GarminConnect

    This was used to clean up and correct activities in GarminConnect
    Pre-steps I would do to prepare input file
     - using Categorize function of this script, export activities list from GarminConnect as a CSV
     - open it in Excel
     - update the newType column if needed using one of these values
       - KEEP - do not do anything
       - DELETE - delete the activity from GarminConnect (used to delete duplicates, activities of my wife, etc.)
       - newTypeValue - change activity type (e.g. inline skating was often marked as running), value represents a key to ACTIVITY_TYPES defined above
     - save it as a CSV
     """

    # INPUT PARAMETERS
    csv_file = "data/activities_20240521_225519.csv"
    # ###################
    activities = []

    with open(csv_file, newline="") as input_csv:
        reader = csv.reader(input_csv, delimiter=';')
        next(reader, None)
        for row in reader:
            if len(row) < 12:
                print("Invalid row in CSV. Stopping at activity " + str(row))
                return None
            activities.append({'activity_id': row[0], 'new_type': row[11]})

    for activity in activities:
        activity_id = activity.get('activity_id')
        new_type = activity.get('new_type')
        if new_type == "KEEP":
            continue
        if new_type == "DELETE":
            api.delete_activity(activity_id)
            continue
        new_type_values = ACTIVITY_TYPES.get(new_type)
        if not new_type_values:
            print("Invalid new_type " + str(new_type) + " stopping at activity " + str(activity_id))
            return
        api.set_activity_type(activity_id, new_type_values[0], new_type_values[1], new_type_values[2])

    return None


def upload_manual_activities(api):
    """
    Upload a list of manually created activities to GarminConnect
    This was used to upload a bulk of old activities I had only in my Excel

    STEPS
     - print already existing activities in GarminConnect on the same days
     - if there is at least one, continue only if "forceCreation==True"
     - upload new activities to GarminConnect

    Manual activity definition
     - just basic parameters (date, activity type, distance, duration, average speed, name of the activity), without any GPS information
       - for typeKey values see ACTIVITY_TYPES
       - specify either duration or average speed, the other one gets calculated
    """

    # INPUT PARAMETERS
    force_creation = False  # use with CAUTION, creates activity in GarminConnect even if there is one already on that day
    activities = [  # [YYYY-MM-DD, type_key, distance_in_km, duration_in_min, avg_speed_in_kmh, activity_name]
        ["2009-09-14", "inline_skating", 8, None, 15, "Inline Skating první jízda, z obchodu v Prateru"],
        ["2009-09-15", "inline_skating", 5, None, 15, "Inline Skating škola"],
        ["2009-11-27", "inline_skating", 12, None, 15, "Inline Skating cesta na tělák od U1 a technika"]]

    # #################
    # check for existing activities
    min_start_date = "3000-12-31"
    max_start_date = "0000-01-01"

    for activity in activities:
        start_date = activity[0]
        min_start_date = start_date if start_date < min_start_date else min_start_date
        max_start_date = start_date if start_date > max_start_date else max_start_date

    if min_start_date is None or max_start_date is None:
        raise ValueError("Failed to get min and max start dates")

    existing_activities = api.get_activities(datetime.date.fromisoformat(min_start_date),
                                             datetime.date.fromisoformat(max_start_date))

    conflict_found = False
    for activity in activities:
        start_date = activity[0]
        for existing_activity in existing_activities:
            if existing_activity.get("startTimeLocal")[0:10] == start_date:
                print("Conflict: " + str(activity) + " existing: " + activity_tostring(existing_activity))
                conflict_found = True

    if conflict_found and not force_creation:
        print("\nSTOP - Activities on the same day already exist. Review and adjust or force creation")
        return

    # create new manual activities
    for activity in activities:
        start_date = activity[0]
        type_key = activity[1]
        distance_km = activity[2]
        duration_min = activity[3]
        avg_speed = activity[4]
        activity_name = activity[5]

        if duration_min is None:
            duration_min = (distance_km / avg_speed) * 60

        if start_date is None or type_key is None or distance_km is None or duration_min is None or activity_name is None:
            raise ValueError("Invalid activity " + str(activity))

        return_value = api.create_manual_activity(start_date + "T10:00:00.00", 'Europe/Paris', type_key, distance_km,
                                                  duration_min, activity_name)
        print(str(return_value) + " for " + str(activity))

    return None


def split_and_upload(api):
    """
    Split GPX file and upload activities

    STEPS
      - Load a local GPX file
      - Extract segments (write into new local GPX files)
          (Forerunners use 1 segment per activity but older GPS devices would put multiple activities into one file which is not handled correctly by Garmin, Strava, etc.
          The behavior is sort of inconsistent, but it often leads to situation where the activity contains even the distance between the individual activities, e.g. spanning half of the republic)
      - For each segment
         - Search and list activities in GarminConnect on the same day
         - If "delete==True", delete the existing activity from GarminConnect
         - If "upload==True", upload the segment as a new activity to GarminConnect
            - change type of the uploaded activity based on the specified "activityType"
    """

    # INPUT PARAMETERS
    input_file = "data/export"
    activity_type = "inline"
    delete = False  # use with CAUTION! Deletes from GarminConnect
    upload = False
    # #################
    content = ET.parse(input_file + '.gpx')
    item_count = len(content.getroot())

    for index_to_keep in range(item_count):
        root = ET.parse(input_file + '.gpx').getroot()
        for i in reversed(range(len(root))):
            if i != index_to_keep:
                del root[i]
        output_xml = ET.tostring(root, encoding="unicode").replace("ns0:", "").replace(":ns0", "")
        timestamp = root[0][0][0][1].text
        output_filename = input_file + "_" + timestamp + ".gpx"
        print("Writing into " + output_filename)
        with open(output_filename, "w") as output_file:
            output_file.write(output_xml)

        existing_activities = api.get_activities_by_date(datetime.datetime.fromisoformat(timestamp),
                                                         datetime.datetime.fromisoformat(timestamp))
        for activity in existing_activities:
            print(" - Existing: " + activity_tostring(activity))
            if delete:
                api.delete_activity(activity.get("activityId"))
                print(" - deleted")

        if len(existing_activities) > 1:
            print(
                "WARN - multiple activities in one day. This will likely need manual adjustment. Uploaded activity may get deleted by the next activity")

        if upload:
            print(" - Uploading")
            response = api.upload_activity(output_filename)
            print(" - " + str(response))
            time.sleep(3)

        existing_activities = api.get_activities_by_date(datetime.datetime.fromisoformat(timestamp),
                                                         datetime.datetime.fromisoformat(timestamp))
        activity_id = None
        for activity in existing_activities:
            if activity.get("startTimeGMT").replace(" ", "T") + "Z" == timestamp:
                activity_id = activity.get("activityId")
                break

        if activity_id:
            new_type_values = ACTIVITY_TYPES.get(activity_type)
            api.set_activity_type(activity_id, new_type_values[0], new_type_values[1], new_type_values[2])
        else:
            print(
                " - ERROR - did not find activityId of the newly uploaded activity - you need to adjust activity type manually")

    return None


# Main program
api = init_api()

# Pick one function you want to process, comment out everything else

# split_and_upload(api)
# upload_manual_activities(api)
# update_activity_type(api)
# categorize_activities(api)
get_activity_by_id(api, 15611628640)

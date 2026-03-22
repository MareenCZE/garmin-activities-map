#!/usr/bin/env python3
import os.path

import downloader
import storage
from common import logger, config
import ftpuploader
import mapgenerator


# ##########################################################
# Main program
# ##########################################################

output_map_filename = config["output"]["map-filename"]
config_mode = config["mode"]

if config_mode["downloader"] == "ON":
    downloader.download_new_activities()

if config_mode["map-creator"] == "ON":
    activities = storage.load_activities_from_csv()
    logger.info(f"Loaded {len(activities)} activities")

    mapgenerator.create_map_with_activities(activities, output_map_filename)
    logger.info(f"Generated {output_map_filename}. Size: {round(os.path.getsize(output_map_filename) / 1048576, 2)} MB")

if config_mode["uploader"] == "ON":
    # Use the new upload function that handles HTML + JSON data files
    ftpuploader.upload_map_with_data_to_ftp_incremental(output_map_filename)

utility_mode = config_mode["utility-mode"]
if utility_mode != "OFF":
    if utility_mode == "REDOWNLOAD":
        downloader.redownload_activity(config_mode["activity-id"])
    elif utility_mode == "REGENERATE_COORDINATES":
        downloader.regenerate_coordinates()
    elif utility_mode == "REGENERATE_CSV":
        downloader.regenerate_csv()
    elif utility_mode == "RESORT_CSV":
        storage.resort_database()
    elif utility_mode == "ENCRYPT_FTP_PASSWORD":
        ftpuploader.encrypt_password()

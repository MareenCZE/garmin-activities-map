#!/usr/bin/env python3
import os.path

import downloader
import minifier
import storage
from common import logger, config
import ftpuploader
import mapgenerator


# ##########################################################
# Main program
# ##########################################################

output_map_filename = config["output"]["map-filename"]
output_map_minified_filename = config["output"]["map-minified-filename"]
config_mode = config["mode"]

if config_mode["downloader"] == "ON":
    downloader.download_new_activities()

if config_mode["map-creator"] == "ON":
    activities = storage.load_activities_from_csv()
    logger.info(f"Loaded {len(activities)} activities")

    mapgenerator.create_map_with_activities(activities, output_map_filename)
    if config_mode["date-filter"] == "ON":
        mapgenerator.add_date_range_filter(output_map_filename)
    logger.info(f"Generated {output_map_filename}. Size: {round(os.path.getsize(output_map_filename) / 1048576, 2)} MB")

if config_mode["minifier"] == "ON":
    minifier.minify(output_map_filename, output_map_minified_filename)
    logger.info(
        f"Minified output saved into {output_map_minified_filename}. Size: {round(os.path.getsize(output_map_minified_filename) / 1048576, 2)} MB")

if config_mode["uploader"] == "ON":
    filename = output_map_minified_filename if config_mode["minifier"] == "ON" else output_map_filename
    ftpuploader.upload_file_to_ftp(filename)

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

#!/usr/bin/env python3
import os.path

import downloader
import minifier
import storage
from common import logger
import ftpuploader
import mapgenerator

OUTPUT_MAP_FILENAME = 'data/activities_map.html'
OUTPUT_MAP_MINIFIED_FILENAME = 'data/activities_map.min.html'


# Use this class to control what steps are to be executed.
# Typical use case is to use DOWNLOAD, ON, ON, ON, OFF which will do all the processing from downloading new activities from GarminConnect
# over generating the map to uploading the map to an FTP site.
class Mode:
    def __init__(self):
        # Download activities from GarminConnect? Supported values:
        #  - DOWNLOAD_NEW
        #  - REDOWNLOAD (for this mode activity_id needs to be specified below)
        #  - OFF
        self.downloader_mode = "DOWNLOAD_NEW"
        # Generate map from activities? Supported values:
        #  - ON
        #  - OFF
        self.map_creator_mode = "ON"
        # Minify generated map? Supported values:
        #  - ON
        #  - OFF
        self.minifier_mode = "ON"
        # Upload the map to an FTP site? Supported values:
        #  - ON
        #  - OFF
        self.uploader_mode = "ON"
        # Utility operations. To be used in exceptional cases when you do code changes or manual data changes. Supported values:
        #  - REGENERATE_COORDINATES
        #  - REGENERATE_CSV
        #  - RESORT_CSV
        #  - OFF
        self.utility_mode = "OFF"

        # ID of activity to re-download. Applies only when downloader_mode==REDOWNLOAD
        self.activity_id = None
        # Highlight activities on mouse hover. Makes output larger (7.8 MB instead of 6.3 MB after minification).
        # Applies only when map_creator_mode==ON
        self.enable_activity_highlighting = True


# ##########################################################
# Main program
# ##########################################################

mode = Mode()

if mode.downloader_mode != "OFF":
    if mode.downloader_mode == "DOWNLOAD_NEW":
        downloader.download_new_activities()
    elif mode.downloader_mode == "REDOWNLOAD":
        downloader.redownload_activity(mode.activity_id)

if mode.map_creator_mode == "ON":
    activities = storage.load_activities_from_csv()
    logger.info(f"Loaded {len(activities)} activities")

    mapgenerator.create_map_with_activities(activities, OUTPUT_MAP_FILENAME, mode.enable_activity_highlighting)
    logger.info(f"Generated {OUTPUT_MAP_FILENAME}. Size: {round(os.path.getsize(OUTPUT_MAP_FILENAME) / 1048576, 2)} MB")

if mode.minifier_mode == "ON":
    minifier.minify(OUTPUT_MAP_FILENAME, OUTPUT_MAP_MINIFIED_FILENAME)
    logger.info(
        f"Minified output saved into {OUTPUT_MAP_MINIFIED_FILENAME}. Size: {round(os.path.getsize(OUTPUT_MAP_MINIFIED_FILENAME) / 1048576, 2)} MB")

if mode.uploader_mode == "ON":
    filename = OUTPUT_MAP_MINIFIED_FILENAME if mode.minifier_mode == "ON" else OUTPUT_MAP_FILENAME
    ftpuploader.upload_file_to_ftp(filename)

if mode.utility_mode != "OFF":
    if mode.utility_mode == "REGENERATE_COORDINATES":
        downloader.regenerate_coordinates()
    elif mode.utility_mode == "REGENERATE_CSV":
        downloader.regenerate_csv()
    elif mode.utility_mode == "RESORT_CSV":
        storage.resort_database()

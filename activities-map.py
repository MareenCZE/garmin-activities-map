#!/usr/bin/env python3
import argparse
import os.path

import downloader
import storage
from common import logger, config
import ftpuploader
import mapgenerator

# ##########################################################
# Main program
#
# Behaviour is driven by the [mode] table in config. The command-line options
# below override those config values for a single run, so automated/scheduled
# runs (e.g. cron) don't need to edit config files. With no options, config
# alone decides what happens.
# ##########################################################

ON_OFF = ("ON", "OFF")
UTILITY_MODES = ("OFF", "REDOWNLOAD", "REGENERATE_COORDINATES", "REGENERATE_CSV",
                 "RESORT_CSV", "ENCRYPT_FTP_PASSWORD")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Download Garmin activities, build the map, and optionally upload it. "
                    "Options override the [mode] settings from config for this run "
                    "(handy for scheduling); anything not passed keeps its config value.")
    parser.add_argument("--downloader", choices=ON_OFF,
                        help="download new activities from Garmin Connect")
    parser.add_argument("--map-creator", choices=ON_OFF, dest="map_creator",
                        help="generate the map from stored activities")
    parser.add_argument("--uploader", choices=ON_OFF,
                        help="upload the generated map to the configured FTP site")
    parser.add_argument("--utility-mode", choices=UTILITY_MODES, dest="utility_mode",
                        help="run a one-off maintenance operation instead of/along with the stages")
    parser.add_argument("--activity-id", dest="activity_id",
                        help="activity id used by --utility-mode REDOWNLOAD")
    return parser.parse_args(argv)


def apply_mode_overrides(args):
    """Overlay any command-line options onto config['mode'] (None means 'not given')."""
    mode = config["mode"]
    overrides = {
        "downloader": args.downloader,
        "map-creator": args.map_creator,
        "uploader": args.uploader,
        "utility-mode": args.utility_mode,
        "activity-id": args.activity_id,
    }
    for key, value in overrides.items():
        if value is not None:
            logger.info(f"Overriding [mode].{key} = {value} (from command line)")
            mode[key] = value


def run():
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


def main(argv=None):
    apply_mode_overrides(parse_args(argv))
    run()


if __name__ == "__main__":
    main()

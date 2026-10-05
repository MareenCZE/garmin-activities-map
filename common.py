#!/usr/bin/env python3
import logging
import os.path
from getpass import getpass

from garminconnect import (Garmin, GarminConnectAuthenticationError, GarminConnectConnectionError,
                           GarminConnectTooManyRequestsError)
import tomllib
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
config = {}


def init_api() -> Garmin:
    """Initialize Garmin API with your credentials."""
    token_store = config["storage"]["directory-token-store"]

    try:
        # Using the token file in the directory; an expiring token is refreshed and saved back
        logger.info(f"Trying to login to Garmin Connect using token data from directory '{token_store}'")

        garmin = Garmin()
        garmin.login(token_store)

    except GarminConnectAuthenticationError:
        # No usable tokens (missing, rejected or in the old pre-0.3 format). You'll need to log in again
        logger.info("Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
              f"They will be stored in '{token_store}' for future use.\n")
        try:
            email, password = get_credentials()

            garmin = Garmin(email=email, password=password, is_cn=False, prompt_mfa=get_mfa)
            # Logs in and saves the token file to the directory for next login
            garmin.login(token_store)
            logger.info(f"Login tokens stored in '{token_store}' directory for future use.\n")
        except (GarminConnectAuthenticationError, GarminConnectConnectionError,
                GarminConnectTooManyRequestsError) as err:
            logger.error(err)
            return None
    except (GarminConnectConnectionError, GarminConnectTooManyRequestsError) as err:
        logger.error(err)
        return None

    return garmin


def get_credentials():
    """Get user credentials."""

    email = input("Login e-mail: ")
    password = getpass("Enter password: ")

    return email, password


def get_mfa():
    """Get MFA."""

    return input("MFA one-time code: ")


def recursive_update(dict1, dict2):
    for key, value in dict2.items():
        if isinstance(value, dict):
            dict1[key] = recursive_update(dict1.get(key, {}), value)
        else:
            dict1[key] = value
    return dict1


def load_config():
    global config
    with open("config-default.toml", "rb") as default_file:
        config = tomllib.load(default_file)

    if os.path.exists("config-local.toml"):
        with open("config-local.toml", "rb") as local_file:
            recursive_update(config, tomllib.load(local_file))
    else:
        logger.info("Local config file not found. Creating an empty config-local.toml")
        with open("config-local.toml", "w") as local_file:
            local_file.write("# Put your personal configuration and overrides of default config into this file")

    logger.debug("Config values:\n" + json.dumps(config, indent=2))


load_config()

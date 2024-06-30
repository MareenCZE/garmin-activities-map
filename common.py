#!/usr/bin/env python3
import logging
import os
from getpass import getpass

import requests
from garminconnect import (Garmin, GarminConnectAuthenticationError)
from garth.exc import GarthHTTPError

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
token_store = os.getenv("GARMINTOKENS") or "~/.garminconnect"


def init_api():
    """Initialize Garmin API with your credentials."""

    try:
        # Using Oauth1 and OAuth2 token files from directory
        print(f"Trying to login to Garmin Connect using token data from directory '{token_store}'...\n")

        garmin = Garmin()
        garmin.login(token_store)

    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        # Session is expired. You'll need to log in again
        print("Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
              f"They will be stored in '{token_store}' for future use.\n")
        try:
            email, password = get_credentials()

            garmin = Garmin(email=email, password=password, is_cn=False, prompt_mfa=get_mfa)
            garmin.login()
            # Save Oauth1 and Oauth2 token files to directory for next login
            garmin.garth.dump(token_store)
            print(f"Oauth tokens stored in '{token_store}' directory for future use. (first method)\n")
        except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError,
                requests.exceptions.HTTPError) as err:
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

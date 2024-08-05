import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import phonenumbers
import requests
from validate_email import validate_email

from meshapi.exceptions import AddressAPIError, AddressError, OpenDataAPIError
from meshapi.util.constants import DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS, INVALID_ALTITUDE
from meshapi.zips import NYCZipCodes
from meshdb.utils.spreadsheet_import.building.constants import INVALID_BIN_NUMBERS
from meshdb.utils.spreadsheet_import.building.pelias import humanify_street_address

NYC_PLANNING_LABS_GEOCODE_URL = "https://geosearch.planninglabs.nyc/v2/search"
DOB_BUILDING_HEIGHT_API_URL = "https://data.cityofnewyork.us/resource/qb5r-6dgf.json"


def validate_email_address(email_address: str) -> bool:
    return validate_email(
        email_address=email_address,
        check_format=True,
        check_blacklist=True,
        check_dns=True,
        dns_timeout=5,
        check_smtp=False,
    )


# Expects country code!!!!
def validate_phone_number(phone_number: str) -> bool:
    try:
        parsed = phonenumbers.parse(phone_number, None)
        if not phonenumbers.is_possible_number(parsed):
            return False
    except phonenumbers.NumberParseException:
        return False
    return True


# Used to obtain info about addresses within NYC. Uses a pair of APIs
# hosted by the city with all kinds of good info. Unfortunately, there's
# not a solid way to check if an address is actually _within_ NYC, so this
# is gated by OSMAddressInfo.
@dataclass
class NYCAddressInfo:
    street_address: str
    city: str
    state: str
    zip: int
    longitude: float
    latitude: float
    altitude: float | None
    bin: int | None

    def __init__(self, street_address: str, city: str, state: str, zip_code: int):
        if state != "New York" and state != "NY":
            raise ValueError(f"(NYC) State '{state}' is not New York.")

        self.address = f"{street_address}, {city}, {state} {zip_code}"

        try:
            # Look up BIN in NYC Planning's Authoritative Search
            # This one always returns a "best effort" search
            query_params = {
                "text": self.address,
                "size": "1",
            }
            nyc_planning_req = requests.get(
                NYC_PLANNING_LABS_GEOCODE_URL,
                params=query_params,
                timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS,
            )
            nyc_planning_resp = json.loads(nyc_planning_req.content.decode("utf-8"))
        except Exception:
            logging.exception("Got exception querying geosearch.planninglabs.nyc")
            raise AddressAPIError

        if len(nyc_planning_resp["features"]) == 0:
            raise AddressError(f"(NYC) Address '{self.address}' not found in geosearch.planninglabs.nyc.")

        # If we enter something not within NYC, the API will still give us
        # the closest matching street address it can find, so check that
        # the ZIP of what we entered matches what we got.

        # FIXME (willnilges): Found an edge case where if you enter an address
        # that's not in the Zip code, it will print the "not within city limits"
        # error. Either the error message needs to be re-worked, or additional
        # validation is required to figure out exactly what is wrong.
        found_zip = int(nyc_planning_resp["features"][0]["properties"]["postalcode"])
        if found_zip != zip_code:
            raise AddressError(
                f"(NYC) Could not find address '{street_address}, {city}, {state} {zip_code}'. "
                f"Zip code ({zip_code}) is incorrect or not within city limits"
            )

        addr_props = nyc_planning_resp["features"][0]["properties"]

        # Get the rest of the address info
        self.street_address = humanify_street_address(f"{addr_props['housenumber']} {addr_props['street']}")

        self.city = addr_props["borough"].replace("Manhattan", "New York")
        self.state = addr_props["region_a"]
        self.zip = int(addr_props["postalcode"])

        # TODO (willnilges): Bail if no BIN. Given that we're guaranteeing this is NYC, if
        # there is no BIN, then we've really foweled something up
        if int(addr_props["addendum"]["pad"]["bin"]) in INVALID_BIN_NUMBERS:
            raise AddressError(
                f"(NYC) Could not find address '{street_address}, {city}, {state} {zip_code}'. "
                f"DOB API returned invalid BIN: {addr_props['addendum']['pad']['bin']}"
            )
        self.bin = addr_props["addendum"]["pad"]["bin"]
        self.longitude, self.latitude = nyc_planning_resp["features"][0]["geometry"]["coordinates"]

        # Now that we have the bin, we can definitively get the height from
        # NYC OpenData
        try:
            query_params = {
                "$where": f"bin={self.bin}",
                "$select": "heightroof,groundelev",
                "$limit": "1",
            }
            nyc_dataset_req = requests.get(
                DOB_BUILDING_HEIGHT_API_URL,
                params=query_params,
                timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS,
            )
            nyc_dataset_resp = json.loads(nyc_dataset_req.content.decode("utf-8"))

            if len(nyc_dataset_resp) == 0:
                logging.warning(f"Empty response from nyc open data about altitude of ({self.bin})")
                raise OpenDataAPIError
            else:
                # Convert relative to ground altitude to absolute altitude AMSL,
                # convert feet to meters, and round to the nearest 0.1 m
                FEET_PER_METER = 3.28084
                self.altitude = round(
                    (float(nyc_dataset_resp[0]["heightroof"]) + float(nyc_dataset_resp[0]["groundelev"]))
                    / FEET_PER_METER,
                    1,
                )
        except OpenDataAPIError:
            self.altitude = INVALID_ALTITUDE
            logging.warning(
                f"(NYC) DOB BIN ({self.bin}) not found in NYC OpenData while trying to query for altitude information"
            )
        except Exception:
            self.altitude = INVALID_ALTITUDE
            logging.exception(f"An error occurred while trying to find ({self.bin}) in NYC OpenData")


def geocode_nyc_address(street_address: str, city: str, state: str, zip_code: int) -> Optional[NYCAddressInfo]:
    # We only support the five boroughs of NYC at this time
    if not NYCZipCodes.match_zip(zip_code):
        raise ValueError(f"Non-NYC zip code detected: {zip_code}")

    attempts_remaining = 2
    while attempts_remaining > 0:
        attempts_remaining -= 1
        try:
            nyc_addr_info = NYCAddressInfo(street_address, city, state, zip_code)
            return nyc_addr_info
        # If the user has given us an invalid address. Tell them to buzz
        # off.
        except AddressError as e:
            logging.exception("AddressError when validating address")
            # Raise to next level
            raise e

        # If we get any other error, then there was probably an issue
        # using the API, and we should wait a bit and re-try
        except (AddressAPIError, Exception):
            logging.exception("(NYC) Something went wrong validating the address. Re-trying...")
            time.sleep(3)

    # If we run out of tries, bail.
    logging.warning(f"Could not parse address: {street_address}, {city}, {state}, {zip_code}")
    return None

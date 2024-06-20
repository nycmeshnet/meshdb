import json
import logging
from dataclasses import dataclass

import phonenumbers
import requests
from django.core.exceptions import ValidationError
from validate_email import validate_email

from meshapi.exceptions import AddressAPIError, AddressError, OpenDataAPIError
from meshapi.util.constants import DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS, INVALID_ALTITUDE
from meshdb.utils.spreadsheet_import.building.constants import INVALID_BIN_NUMBERS
from meshdb.utils.spreadsheet_import.building.pelias import humanify_street_address


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


def validate_phone_number_field(phone_number: str):
    if not validate_phone_number(phone_number):
        raise ValidationError(f"Invalid phone number: {phone_number}")


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

    def __init__(self, street_address: str, city: str, state: str, zip: int):
        if state != "New York" and state != "NY":
            raise ValueError(f"(NYC) State '{state}' is not New York.")

        self.address = f"{street_address}, {city}, {state} {zip}"

        try:
            # Look up BIN in NYC Planning's Authoritative Search
            # This one always returns a "best effort" search
            query_params = {
                "text": self.address,
                "size": "1",
            }
            nyc_planning_req = requests.get(
                "https://geosearch.planninglabs.nyc/v2/search",
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
        if found_zip != zip:
            raise AddressError(
                f"(NYC) Could not find address '{street_address}, {city}, {state} {zip}'. "
                f"Zip code ({zip}) is probably not within city limits"
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
            raise AddressAPIError
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
                "https://data.cityofnewyork.us/resource/qb5r-6dgf.json",
                params=query_params,
                timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS,
            )
            nyc_dataset_resp = json.loads(nyc_dataset_req.content.decode("utf-8"))

            if len(nyc_dataset_resp) == 0:
                logging.warning(f"Empty response from nyc open data about altitude of ({self.bin})")
                raise OpenDataAPIError
            else:
                self.altitude = float(nyc_dataset_resp[0]["heightroof"]) + float(nyc_dataset_resp[0]["groundelev"])
        except OpenDataAPIError:
            self.altitude = INVALID_ALTITUDE
            logging.warning(
                f"(NYC) DOB BIN ({self.bin}) not found in NYC OpenData while trying to query for altitude information"
            )
        except Exception:
            self.altitude = INVALID_ALTITUDE
            logging.exception(f"An error occurred while trying to find ({self.bin}) in NYC OpenData")

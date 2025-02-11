import json
import logging
import os
import time
from dataclasses import dataclass
from typing import List, Optional

import phonenumbers
import requests
from django.core.exceptions import ValidationError
from flags.state import flag_state
from validate_email import validate_email_or_fail
from validate_email.exceptions import (
    DNSTimeoutError,
    EmailValidationError,
    SMTPCommunicationError,
    SMTPTemporaryError,
    TLSNegotiationError,
)

from meshapi.exceptions import AddressAPIError, AddressError, OpenDataAPIError
from meshapi.util.constants import DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS, INVALID_ALTITUDE
from meshapi.zips import NYCZipCodes

from .pelias import humanify_street_address

RECAPTCHA_SECRET_KEY_V2 = os.environ.get("RECAPTCHA_SERVER_SECRET_KEY_V2")
RECAPTCHA_SECRET_KEY_V3 = os.environ.get("RECAPTCHA_SERVER_SECRET_KEY_V3")
RECAPTCHA_INVISIBLE_TOKEN_SCORE_THRESHOLD = float(os.environ.get("RECAPTCHA_INVISIBLE_TOKEN_SCORE_THRESHOLD", 0.5))

NYC_PLANNING_LABS_GEOCODE_URL = "https://geosearch.planninglabs.nyc/v2/search"
# "Building Footprint" Dataset (https://data.cityofnewyork.us/City-Government/Building-Footprints/5zhs-2jue/about_data)
DOB_BUILDING_HEIGHT_API_URL = "https://data.cityofnewyork.us/resource/5zhs-2jue.json"
RECAPTCHA_TOKEN_VALIDATION_URL = "https://www.google.com/recaptcha/api/siteverify"


INVALID_BIN_NUMBERS = [-2, -1, 0, 1000000, 2000000, 3000000, 4000000]


def validate_email_address(email_address: str) -> Optional[bool]:
    try:
        return validate_email_or_fail(
            email_address=email_address,
            check_format=True,
            check_blacklist=True,
            check_dns=True,
            dns_timeout=5,
            check_smtp=False,
        )
    except SMTPTemporaryError:
        # SMTPTemporaryError indicates address validity
        # is ambiguous. We give the submitter the benefit of the doubt in this case
        return True
    except (DNSTimeoutError, SMTPCommunicationError, TLSNegotiationError) as error:
        # These errors indicate a transient failure in our ability to validate the requested email,
        # re-raise the exception to trigger a 500 at the top level handler
        raise error
    except EmailValidationError:
        # Failures for any other reason indicate the email address is invalid, and we should 400 them
        return False


def normalize_phone_number(phone_number: str) -> str:
    return phonenumbers.format_number(
        phonenumbers.parse(phone_number, "US"),
        phonenumbers.PhoneNumberFormat.INTERNATIONAL,
    )


def validate_phone_number(phone_number: str) -> Optional[phonenumbers.PhoneNumber]:
    try:
        parsed = phonenumbers.parse(phone_number, "US")
        if not phonenumbers.is_possible_number(parsed):
            return None
        return parsed
    except phonenumbers.NumberParseException:
        return None


# Used to obtain info about addresses within NYC. Uses a pair of APIs
# hosted by the city with all kinds of good info. Unfortunately, there's
# not a solid way to check if an address is actually _within_ NYC, so this
# is gated by OSMAddressInfo.
@dataclass
class NYCAddressInfo:
    street_address: str
    city: str
    state: str
    zip: str
    longitude: float
    latitude: float
    altitude: float | None
    bin: int | None

    def __init__(self, street_address: str, city: str, state: str, zip_code: str):
        if state != "New York" and state != "NY":
            raise ValueError(f"(NYC) State '{state}' is not New York.")

        # We only support the five boroughs of NYC at this time
        if not NYCZipCodes.match_zip(zip_code):
            raise ValueError(f"Non-NYC zip code detected: {zip_code}")

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

        # For some insane reason this is an integer, so we have to cast it to a string
        found_zip = str(nyc_planning_resp["features"][0]["properties"]["postalcode"])
        if found_zip != zip_code:
            raise AddressError(
                f"(NYC) Could not find address '{street_address}, {city}, {state} {zip_code}'. "
                f"Zip code ({zip_code}) is incorrect or not within city limits"
            )

        addr_props = nyc_planning_resp["features"][0]["properties"]

        # Get the rest of the address info
        self.street_address = humanify_street_address(f"{addr_props['housenumber']} {addr_props['street']}")

        self.city = addr_props["borough"].replace("Manhattan", "New York")

        # Queens addresses are special and different, but it seems the neighborhood name
        # that the city gives us is always a good value for "City"
        if self.city == "Queens":
            self.city = addr_props.get("neighbourhood", "Queens")

        self.state = addr_props["region_a"]
        self.zip = str(addr_props["postalcode"])

        if (
            not addr_props.get("addendum", {}).get("pad", {}).get("bin")
            or int(addr_props["addendum"]["pad"]["bin"]) in INVALID_BIN_NUMBERS
        ):
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


def validate_multi_phone_number_field(phone_number_list: List[str]) -> None:
    for num in phone_number_list:
        validate_phone_number_field(num)


def validate_phone_number_field(phone_number: str) -> None:
    if not validate_phone_number(phone_number):
        raise ValidationError(f"Invalid phone number: {phone_number}")


def geocode_nyc_address(street_address: str, city: str, state: str, zip_code: str) -> Optional[NYCAddressInfo]:
    attempts_remaining = 2
    while attempts_remaining > 0:
        attempts_remaining -= 1
        try:
            nyc_addr_info = NYCAddressInfo(street_address, city, state, zip_code)
            return nyc_addr_info
        # If the user has given us an invalid address. Tell them to buzz
        # off.
        except (AddressError, ValueError) as e:
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


def check_recaptcha_token(token: Optional[str], server_secret: str, remote_ip: Optional[str]) -> float:
    payload = {"secret": server_secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    captcha_response = requests.post(
        RECAPTCHA_TOKEN_VALIDATION_URL,
        payload,
    )

    captcha_response.raise_for_status()

    response_json = captcha_response.json()

    # If "success" is missing or false, throw an error that this is an invalid token
    if not response_json.get("success"):
        raise ValueError("Invalid recaptcha token")

    # If there is no score in the response, we are dealing with a v2 token,
    # which has no concept of score, only binary success/failure of the manual
    # checkbox captcha. In this case, we can be confident this is a human since
    # they have completed the checkbox captcha, so we return 1.0 (100% human score)
    return response_json.get("score", 1.0)


def validate_recaptcha_tokens(
    recaptcha_invisible_token: Optional[str], recaptcha_checkbox_token: Optional[str], remote_ip: Optional[str]
) -> None:
    if not RECAPTCHA_SECRET_KEY_V3 or not RECAPTCHA_SECRET_KEY_V2:
        raise EnvironmentError(
            "Enviornment variables RECAPTCHA_SERVER_SECRET_KEY_V2 and RECAPTCHA_SERVER_SECRET_KEY_V3 must be "
            "set in order to validate recaptcha tokens"
        )

    # If we have a checkbox token, just check that token is valid, and if it is, we are good, since
    # completing the checkbox is a good indication of human-ness
    if recaptcha_checkbox_token:
        check_recaptcha_token(recaptcha_checkbox_token, RECAPTCHA_SECRET_KEY_V2, remote_ip)
        # The above call will throw if the token is invalid, so if we reach this point we are done
        # validating
        return

    # If we don't have a checkbox token, get the score associated with the "invisible" token
    # and if it's too low, throw an exception so we 401 them
    # (which will prompt them to submit a checkbox in the frontend)
    invisible_token_score = check_recaptcha_token(recaptcha_invisible_token, RECAPTCHA_SECRET_KEY_V3, remote_ip)

    if invisible_token_score < RECAPTCHA_INVISIBLE_TOKEN_SCORE_THRESHOLD:
        raise ValueError(
            f"Score of {invisible_token_score} is less than our threshold of "
            f"{RECAPTCHA_INVISIBLE_TOKEN_SCORE_THRESHOLD}"
        )

    if flag_state("JOIN_FORM_FAIL_ALL_INVISIBLE_RECAPTCHAS"):
        raise ValueError(
            "Feature flag JOIN_FORM_FAIL_ALL_INVISIBLE_RECAPTCHAS enabled, failing validation "
            "even though this request should have succeeded"
        )

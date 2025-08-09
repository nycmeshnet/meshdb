import json
import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import phonenumbers
import requests
from django.core.exceptions import ValidationError
from flags.state import flag_state
from requests.adapters import HTTPAdapter, Retry
from validate_email import validate_email_or_fail
from validate_email.exceptions import (
    DNSTimeoutError,
    EmailValidationError,
    SMTPCommunicationError,
    SMTPTemporaryError,
    TLSNegotiationError,
)

from meshapi.exceptions import AddressAPIError, InvalidAddressError, UnsupportedAddressError
from meshapi.util.constants import DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS, INVALID_ALTITUDE
from meshapi.zips import NYCZipCodes

from .pelias import humanify_street_address

RECAPTCHA_SECRET_KEY_V2 = os.environ.get("RECAPTCHA_SERVER_SECRET_KEY_V2")
RECAPTCHA_SECRET_KEY_V3 = os.environ.get("RECAPTCHA_SERVER_SECRET_KEY_V3")
RECAPTCHA_INVISIBLE_TOKEN_SCORE_THRESHOLD = float(os.environ.get("RECAPTCHA_INVISIBLE_TOKEN_SCORE_THRESHOLD", 0.5))

# This API sits in front of an elasticsearch database based off the Property Address Directory (PAD)
# It is our main source of truth for NYC-based addresses.
# https://geosearch.planninglabs.nyc
# https://www.nyc.gov/content/planning/pages/resources/datasets/pad
NYC_GEOSEARCH_API = "https://geosearch.planninglabs.nyc/v2/search"
# "Building Footprint" Dataset (https://data.cityofnewyork.us/City-Government/Building-Footprints/5zhs-2jue/about_data)
BUILDING_FOOTPRINTS_API = "https://data.cityofnewyork.us/resource/5zhs-2jue.json"
# https://data.cityofnewyork.us/Housing-Development/DOB-NYC-New-Buildings/6xbh-bxki/data_preview
DOB_NEW_BUILDINGS_API_URL = "https://data.cityofnewyork.us/resource/6xbh-bxki.json"
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
    sesssion: requests.Session  # For all the HTTP requests we have to do
    street_address: str
    city: str
    state: str
    zip: str
    longitude: float
    latitude: float
    altitude: float | None
    bin: int | None

    def __init__(self, street_address: str, city: str, state: str, zip_code: str):
        self.session = get_requests_session_with_retries()
        if state != "New York" and state != "NY":
            logging.error(f"State '{state}' is not New York.")
            raise UnsupportedAddressError

        # This method is only compatible with the 5 boroughs of NYC
        if not NYCZipCodes.match_zip(zip_code):
            logging.error(f"Zip code '{zip_code}' does not appear in our zip code database.")
            raise UnsupportedAddressError

        self.address = f"{street_address}, {city}, {state} {zip_code}"

        try:
            # Look up BIN in NYC Planning's Authoritative Search
            # This one always returns a "best effort" search
            query_params = {
                "text": self.address,
                "size": "1",
            }
            nyc_planning_req = self.session.get(
                NYC_GEOSEARCH_API,
                params=query_params,
                timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS,
            )
            nyc_geosearch_resp = json.loads(nyc_planning_req.content.decode("utf-8"))
        except Exception:
            logging.exception("An exception occurred while querying geosearch.planninglabs.nyc")
            raise AddressAPIError

        if len(nyc_geosearch_resp["features"]) == 0:
            logging.error("Address not found in geosearch.planninglabs.nyc.")
            raise InvalidAddressError

        addr_props = nyc_geosearch_resp["features"][0]["properties"]

        # If we enter something not within NYC, the API will still give us
        # the closest matching street address it can find, so check that
        # the ZIP of what we entered matches what we got.

        found_zip = str(addr_props["postalcode"])
        if found_zip != zip_code:
            logging.error(
                f"Zip code '{zip_code}' does not match zip code '{found_zip}'"
                "returned from geosearch.planninglabs.nyc"
            )
            raise InvalidAddressError

        # Get the rest of the address info
        self.street_address = humanify_street_address(f"{addr_props['housenumber']} {addr_props['street']}")
        self.city = addr_props["borough"].replace("Manhattan", "New York")
        if self.city == "Queens":
            # Queens addresses are special and different, but it seems the neighborhood name
            # that the city gives us is always a good value for "City"
            self.city = addr_props.get("neighbourhood", "Queens")
        self.state = addr_props["region_a"]
        self.zip = str(addr_props["postalcode"])

        # If geosearch.planninglabs.nyc did not return the BIN, we can check the New Buildings data set
        # based on work permits from the DOB to try backfilling.
        self.bin = addr_props["addendum"]["pad"]["bin"]
        if not self.bin or self.bin in INVALID_BIN_NUMBERS:
            dob_warning_message = (
                f"geosearch.planninglabs.nyc returned invalid BIN: {addr_props['addendum']['pad']['bin']}"
            )
            logging.warning(dob_warning_message + "Falling back to NYC OpenData New Buildings dataset")
            # We're using the addr_props returned from DOB API because
            # they should be in the same format required by NYC Open Data
            open_data_bin = lookup_address_nyc_open_data_new_buildings(
                addr_props["street"],
                addr_props["housenumber"],
                addr_props["borough"].upper(),
                str(addr_props["postalcode"]),
            )

            if not open_data_bin:
                logging.error("NYC OpenData New Buildings returned no data.")
                raise InvalidAddressError

            self.bin = open_data_bin

        self.longitude, self.latitude = nyc_geosearch_resp["features"][0]["geometry"]["coordinates"]
        self.altitude = self.get_height_from_building_footprints_api(self.bin)

    def get_height_from_building_footprints_api(self, bin: int) -> Optional[float]:
        # Now that we have the bin, we can definitively get the height from
        # NYC OpenData Building Footprints
        try:
            query_params = {
                "$where": f"bin={bin}",
                "$select": "height_roof,ground_elevation",
                "$limit": "1",
            }
            nyc_dataset_req = self.session.get(
                BUILDING_FOOTPRINTS_API,
                params=query_params,
                timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS,
            )
            nyc_dataset_req.raise_for_status()
        except Exception:
            logging.exception("[BUILDING_FOOTPRINTS] Exception raised during HTTP Request.")
            return INVALID_ALTITUDE

        nyc_dataset_resp = json.loads(nyc_dataset_req.content.decode("utf-8"))
        if len(nyc_dataset_resp) == 0:
            logging.warning(f"[BUILDING_FOOTPRINTS] Empty response for BIN '{bin}'. Setting Altitude to 0")
            return INVALID_ALTITUDE

        # Convert relative to ground altitude to absolute altitude AMSL,
        # convert feet to meters, and round to the nearest 0.1 m
        FEET_PER_METER = 3.28084
        altitude = round(
            (float(nyc_dataset_resp[0]["height_roof"]) + float(nyc_dataset_resp[0]["ground_elevation"]))
            / FEET_PER_METER,
            1,
        )

        return altitude


def lookup_address_nyc_open_data_new_buildings(
    street_name: str, house_number: str, borough: str, zip_code: str
) -> Optional[int]:
    try:
        session = get_requests_session_with_retries()
        params = {
            "street_name": street_name,
            "house__": house_number,
            "borough": borough,
            "zip_code": zip_code,
        }
        response = session.get(DOB_NEW_BUILDINGS_API_URL, params=params)
        response.raise_for_status()
        # TODO: (wdn) Run the tests and make sure this is accounted for
        # This should be redundant, but we want to preserve previous behavior
        # if response.status_code != 200:
        #     raise HTTPException
    except Exception:
        logging.exception("[NEW_BUILDINGS] Exception raised during HTTP Request.")
        return None

    data = response.json()

    if not data:
        logging.error("[NEW_BUILDINGS] No data found for the specified address.")
        return None

    open_data_bin = data[0].get("bin__")

    # Make sure we get only one BIN
    for d in data:
        if d.get("bin__") != open_data_bin:
            logging.error("[NYC OpenData New Buildings] Returned multiple BINs. I don't know which one is correct!")
            return None

    return int(open_data_bin)


def validate_multi_phone_number_field(phone_number_list: List[str]) -> None:
    for num in phone_number_list:
        validate_phone_number_field(num)


def validate_phone_number_field(phone_number: str) -> None:
    if not validate_phone_number(phone_number):
        raise ValidationError(f"Invalid phone number: {phone_number}")


def geocode_nyc_address(street_address: str, city: str, state: str, zip_code: str) -> NYCAddressInfo:
    logging.info(f"Running NYC geocode for '{street_address}, {city}, {state} {zip_code}'...")
    try:
        return NYCAddressInfo(street_address, city, state, zip_code)
    except (UnsupportedAddressError, InvalidAddressError, AddressAPIError) as e:
        raise e
    except Exception as e:
        # If we get some unknown exception, make sure the exception gets logged
        logging.exception("An exception occurred while running NYC geocode")
        raise e


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


def get_requests_session_with_retries():
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )

    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

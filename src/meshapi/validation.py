import json
import time
import requests
from dataclasses import dataclass
from validate_email import validate_email
import phonenumbers
from geopy.geocoders import Nominatim
from meshapi.exceptions import AddressError


def validate_email_address(email_address):
    return validate_email(
        email_address=email_address,
        check_format=True,
        check_blacklist=True,
        check_dns=True,
        dns_timeout=5,
        check_smtp=False,
    )


# Expects country code!!!!
def validate_phone_number(phone_number):
    try:
        phonenumbers.parse(phone_number, None)
    except phonenumbers.NumberParseException:
        return False
    return True


# Used to obtain information about addresses from the Open Street Map API.
# This is our primiary source of information for addresses outside of NYC.
@dataclass
class OSMAddressInfo:
    address: str
    longitude: float
    latitude: float
    altitude: float
    nyc: bool

    def __init__(self, street_address, city, state, zip):
        geolocator = Nominatim(user_agent="address_lookup")
        address = f"{street_address}, {city}, {state} {zip}"
        location = geolocator.geocode(address)
        if location is None:
            raise AddressError("(OSM) Address not found.")

        self.address = location.address
        # self.county = location.county # Not guaranteed to exist!?
        self.longitude = location.longitude
        self.latitude = location.latitude
        self.altitude = location.altitude  # Usually 0 because very few places have it

        boroughs = ["New York County", "Kings County", "Queens County", "Bronx County", "Richmond County"]
        if any(f"{borough}, City of New York" in self.address for borough in boroughs):
            self.nyc = True
        else:
            self.nyc = False


# Used to obtain info about addresses within NYC. Uses a pair of APIs
# hosted by the city with all kinds of good info. Unfortunately, there's
# not a solid way to check if an address is actually _within_ NYC, so this
# is gated by OSMAddressInfo.
@dataclass
class NYCAddressInfo:
    address: str
    longitude: float
    latitude: float
    altitude: float
    bin: int

    def __init__(self, street_address, city, state, zip):
        if state != "NY":
            raise ValueError("(NYC) State is not New York.")

        self.address = f"{street_address}, {city}, {state} {zip}"

        # Look up BIN in NYC Planning's Authoritative Search
        query_params = {
            "text": self.address,
            "size": 1,
        }
        nyc_planning_req = requests.get(f"https://geosearch.planninglabs.nyc/v2/search", params=query_params)
        nyc_planning_resp = json.loads(nyc_planning_req.content.decode("utf-8"))

        if len(nyc_planning_resp["features"]) == 0:
            raise AddressError("(NYC) Address not found.")

        # If we enter something not within NYC, the API will still give us
        # the closest matching street address it can find, so check that
        # the ZIP of what we entered matches what we got.
        found_zip = int(nyc_planning_resp["features"][0]["properties"]["postalcode"])
        if found_zip != zip:
            raise AddressError(f"(NYC) Could not find address. Zip code ({zip}) is probably not within city limits")

        self.bin = nyc_planning_resp["features"][0]["properties"]["addendum"]["pad"]["bin"]
        self.longitude, self.latitude = nyc_planning_resp["features"][0]["geometry"]["coordinates"]

        # Now that we have the bin, we can definitively get the height from
        # NYC OpenData
        query_params = {
            "$where": f"bin={self.bin}",
            "$select": "heightroof,groundelev",
            "$limit": 1,
        }
        nyc_dataset_req = requests.get(f"https://data.cityofnewyork.us/resource/qb5r-6dgf.json", params=query_params)
        nyc_dataset_resp = json.loads(nyc_dataset_req.content.decode("utf-8"))

        if len(nyc_dataset_resp) == 0:
            raise AddressError(f"(NYC) Bin ({self.bin}) not found.")

        self.altitude = float(nyc_dataset_resp[0]["heightroof"]) + float(nyc_dataset_resp[0]["groundelev"])

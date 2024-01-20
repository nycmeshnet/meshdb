import json
import time
import requests
from dataclasses import dataclass
from validate_email import validate_email
import phonenumbers
from geopy.geocoders import Nominatim
from meshapi.exceptions import AddressError, AddressAPIError
from meshapi.zips import NYCZipCodes

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
    street_address: str
    city: str
    state: str
    zip: int
    longitude: float
    latitude: float
    altitude: float
    nyc: bool

    def __init__(self, street_address: str, city: str, state: str, zip: int):
        geolocator = Nominatim(user_agent="address_lookup")
        address = f"{street_address}, {city}, {state} {zip}"
        location = geolocator.geocode(address, addressdetails=True)
        if location is None:
            raise AddressError(f"(OSM) Address not found for user input: '{address}'")

        r_addr = location.raw["address"]

        self.street_address = f"{r_addr['house_number']} {r_addr['road']}"
        self.city = r_addr["city"]
        self.state = r_addr["state"]
        self.zip = int(r_addr["postcode"])
        self.longitude = location.longitude
        self.latitude = location.latitude
        self.altitude = location.altitude  # Usually 0 because very few places have it

        boroughs = ["New York County", "Kings County", "Queens County", "Bronx County", "Richmond County"]
        if any(borough in r_addr["county"] for borough in boroughs):
            # OSM defines the boroughs in a weird way. Where a sane person
            # would write "City: Brooklyn", they write "City: City of New York"
            # and "Suburb: Brooklyn"
            # So the "suburb" field will give us the borough.
            # FIXME: This adds "Manhattan" as a city which makes no sense
            self.city = r_addr["suburb"]
            self.nyc = True
        else:
            self.nyc = False

        # Python is on a lot of drugs
        # Actually, python _is_ a lot of drugs
        assert isinstance(self.zip, int), "Zip is not an int!?"


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

    def __init__(self, street_address: str, city: str, state: str, zip: int):
        if state != "New York" and state != "NY":
            raise ValueError(f"(NYC) State '{state}' is not New York.")

        self.address = f"{street_address}, {city}, {state} {zip}"

        # Look up BIN in NYC Planning's Authoritative Search
        # This one always returns a "best effort" search
        query_params = {
            "text": self.address,
            "size": 1,
        }
        nyc_planning_req = requests.get(f"https://geosearch.planninglabs.nyc/v2/search", params=query_params)
        nyc_planning_resp = json.loads(nyc_planning_req.content.decode("utf-8"))

        if len(nyc_planning_resp["features"]) == 0:
            raise AddressAPIError(
                f"(NYC) Got bad API response when querying geosearch.planninglabs.nyc for  '{self.address}'."
            )

        # If we enter something not within NYC, the API will still give us
        # the closest matching street address it can find, so check that
        # the ZIP of what we entered matches what we got.
        found_zip = int(nyc_planning_resp["features"][0]["properties"]["postalcode"])
        if found_zip != zip:
            raise AddressError(
                f"(NYC) Could not find address '{street_address}, {city}, {state} {zip}'. Zip code ({zip}) is probably not within city limits"
            )

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
            raise AddressAPIError(
                f"(NYC) DOB BIN ({self.bin}) not found in NYC OpenData while trying to query for altitude information"
            )

        self.altitude = float(nyc_dataset_resp[0]["heightroof"]) + float(nyc_dataset_resp[0]["groundelev"])

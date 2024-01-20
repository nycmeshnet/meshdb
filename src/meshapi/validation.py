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

    def validate(self):
        pass
        # Query the Open Street Map to validate and "standardize" the member's
        # inputs. We're going to use this as the canonical address, and then
        # supplement with NYC API information
        #osm_addr_info = None
        #attempts_remaining = 2
        #while attempts_remaining > 0:
        #    attempts_remaining -= 1
        #    try:
        #        osm_addr_info = OSMAddressInfo(r.street_address, r.city, r.state, r.zip)
        #        if not osm_addr_info.nyc:
        #            print(
        #                f"(OSM) Address '{osm_addr_info.street_address}, {osm_addr_info.city}, {osm_addr_info.state} {osm_addr_info.zip}' is not in NYC"
        #            )
        #        break
        #    # If the user has given us an invalid address, tell them to buzz off.
        #    except AddressError as e:
        #        print(e)
        #        return Response(
        #            f"(OSM) Address '{r.street_address}, {r.city}, {r.state} {r.zip}' not found",
        #            status=status.HTTP_400_BAD_REQUEST,
        #        )
        #    except AssertionError as e:
        #        print(e)
        #        return Response("Unexpected internal state", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        #    # If the API gives us an error, then try again
        #    except (GeocoderUnavailable, Exception) as e:
        #        print(e)
        #        print("(OSM) Something went wrong validating the address. Re-trying...")
        #        time.sleep(3)
        ## If we try multiple times without success, bail.
        #if osm_addr_info == None:
        #    return Response("(OSM) Error validating address", status=status.HTTP_503_SERVICE_UNAVAILABLE)


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

        addr_props = nyc_planning_resp["features"][0]["properties"]

        # Get the rest of the address info
        self.street_address = f"{addr_props['housenumber']} {addr_props['street']}"
        self.city = addr_props["borough"]
        self.state = addr_props["region_a"]
        self.zip = addr_props["postalcode"]
        
        # TODO (willnilges): Bail if no BIN. Given that we're guaranteeing this is NYC, if
        # there is no BIN, then we've really foweled something up
        self.bin = addr_props["addendum"]["pad"]["bin"]
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

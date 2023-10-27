import json
import time
import requests
from dataclasses import dataclass
from validate_email import validate_email
import phonenumbers

# Source: https://www.nyc.gov/assets/doh/downloads/pdf/ah/zipcodetable.pdf
nyc_postal_codes = [
    10463,
    10471,
    10466,
    10469,
    10470,
    10475,
    10458,
    10467,
    10468,
    10461,
    10462,
    10464,
    10465,
    10472,
    10473,
    10453,
    10457,
    10460,
    10451,
    10452,
    10456,
    10454,
    10455,
    10459,
    10474,
    11211,
    11222,
    11201,
    11205,
    11215,
    11217,
    11231,
    11213,
    11212,
    11216,
    11233,
    11238,
    11207,
    11208,
    11220,
    11232,
    11204,
    11218,
    11219,
    11230,
    11203,
    11210,
    11225,
    11226,
    11234,
    11236,
    11239,
    11209,
    11214,
    11228,
    11223,
    11224,
    11229,
    11235,
    11206,
    11221,
    11237,
    10031,
    10032,
    10033,
    10034,
    10040,
    10026,
    10027,
    10030,
    10037,
    10039,
    10029,
    10035,
    10023,
    10024,
    10025,
    10021,
    10028,
    10044,
    10128,
    10001,
    10011,
    10018,
    10019,
    10020,
    10036,
    10010,
    10016,
    10017,
    10022,
    10012,
    10013,
    10014,
    10002,
    10003,
    10009,
    10004,
    10005,
    10006,
    10007,
    10038,
    10280,
    11101,
    11102,
    11103,
    11104,
    11105,
    11106,
    11368,
    11369,
    11370,
    11372,
    11373,
    11377,
    11378,
    11354,
    11355,
    11356,
    11357,
    11358,
    11359,
    11360,
    11361,
    11362,
    11363,
    11364,
    11374,
    11375,
    11379,
    11385,
    11365,
    11366,
    11367,
    11414,
    11415,
    11416,
    11417,
    11418,
    11419,
    11420,
    11421,
    11412,
    11423,
    11432,
    11433,
    11434,
    11435,
    11436,
    11004,
    11005,
    11411,
    11413,
    11422,
    11426,
    11427,
    11428,
    11429,
    11691,
    11692,
    11693,
    11694,
    11695,
    11697,
    10302,
    10303,
    10310,
    10301,
    10304,
    10305,
    10314,
    10306,
    10307,
    10308,
    10309,
    10312,
]


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


def is_nyc_zip(zip):
    return zip in nyc_postal_codes


@dataclass
class NYCAddressInfo:
    address: str
    longitude: float
    latitude: float
    altitude: float
    bin: int

    def __init__(self, street_address, city, state, zip):
        if state != "NY":
            raise ValueError("State is not New York.")

        if not is_nyc_zip(zip):
            raise ValueError("Zip code not within city limits.")

        self.address = f"{street_address}, {city}, {state} {zip}"
        # Look up BIN in NYC Planning's Authoritative Search
        query_params = {
            "text": self.address,
            "size": 1,
        }
        nyc_planning_req = requests.get(f"https://geosearch.planninglabs.nyc/v2/search", params=query_params)
        nyc_planning_resp = json.loads(nyc_planning_req.content.decode("utf-8"))

        if len(nyc_planning_resp["features"]) == 0:
            raise requests.exceptions.HTTPError("Address not found.")

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
            raise requests.exceptions.HTTPError("Bin not found.")

        self.altitude = float(nyc_dataset_resp[0]["heightroof"]) + float(nyc_dataset_resp[0]["groundelev"])

import json
import time
import requests
from dataclasses import dataclass
from validate_email import validate_email
import phonenumbers

# Source: https://www.zip-codes.com/state/ny.asp
# Contains all zips from Richmond, Kings, Queens, Bronx, and New York County
nyc_postal_codes = [11356, 10463, 11202, 11207, 10310, 10024, 11214, 11104, 10003, 11102, 10055, 10033, 10302, 10040, 11379, 10306, 11211, 11229, 11367, 11405, 10451, 10453, 11222, 11362, 10314, 11239, 10467, 11355, 11241, 11230, 10039, 11103, 11228, 10308, 11351, 10045, 11225, 10080, 11109, 11365, 10304, 11206, 11385, 10472, 10021, 10017, 10025, 10004, 10305, 11412, 10473, 11364, 11374, 10037, 10303, 11247, 11366, 11105, 11251, 11372, 11223, 10301, 10023, 11040, 10470, 10462, 11378, 10011, 10027, 11226, 11252, 11373, 11368, 11371, 10020, 10075, 10313, 10312, 10008, 11212, 10016, 10307, 10006, 11216, 10311, 10465, 11380, 10014, 11208, 11354, 11203, 11120, 11386, 11218, 11220, 11213, 10031, 11234, 10060, 11004, 11005, 11233, 11219, 11201, 11217, 10028, 11245, 10454, 10471, 11101, 11224, 10012, 10466, 10460, 11358, 11204, 11243, 10456, 11361, 10007, 10468, 11370, 10475, 10081, 11232, 10459, 10010, 10461, 10069, 11221, 10474, 10044, 11242, 10030, 11411, 10455, 11205, 11237, 11377, 10043, 10034, 11363, 11352, 10032, 10469, 11249, 10457, 10452, 10009, 11001, 10065, 10018, 10029, 11413, 10309, 10019, 10001, 11414, 11236, 10026, 10038, 11256, 10041, 11235, 10036, 11238, 11375, 11416, 11357, 10464, 11215, 10035, 11359, 10002, 10013, 11231, 10022, 11360, 10005, 10458, 11209, 11106, 11369, 11415, 11210]

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

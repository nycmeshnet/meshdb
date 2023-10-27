import json
import time
import requests
from dataclasses import dataclass
from validate_email import validate_email
import phonenumbers

@dataclass
class AddressInfo:
    address: str
    longitude: float
    latitude: float
    altitude: float
    bin: int


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



def validate_street_address(address):
    addr_info = AddressInfo(address, 0.0, 0.0, 0.0, 0)

    # Look up BIN in NYC Planning's Authoritative Search
    query_params = {
        "text": addr_info.address,
    }
    nyc_planning_req = requests.get(f"https://geosearch.planninglabs.nyc/v2/search", params=query_params)
    nyc_planning_resp = json.loads(nyc_planning_req.content.decode("utf-8"))

    if len(nyc_planning_resp["features"]) == 0:
        raise requests.exceptions.HTTPError("Address not found.")

    addr_info.bin = nyc_planning_resp["features"][0]["properties"]["addendum"]["pad"]["bin"]
    addr_info.longitude, addr_info.latitude = nyc_planning_resp["features"][0]["geometry"]["coordinates"]

    # Now that we have the bin, we can definitively get the height from
    # NYC OpenData
    query_params = {
        "$where": f"bin={addr_info.bin}",
        "$select": "heightroof,groundelev",
        "$limit": 1,
    }
    nyc_dataset_req = requests.get(
        f"https://data.cityofnewyork.us/resource/qb5r-6dgf.json", params=query_params
    )
    nyc_dataset_resp = json.loads(nyc_dataset_req.content.decode("utf-8"))

    if len(nyc_dataset_resp) == 0:
        raise requests.exceptions.HTTPError("Bin not found.")

    addr_info.altitude = float(nyc_dataset_resp[0]["heightroof"]) + float(nyc_dataset_resp[0]["groundelev"])

    return addr_info


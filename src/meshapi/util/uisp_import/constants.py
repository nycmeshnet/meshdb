import datetime

EXCLUDED_UISP_DEVICE_CATEGORIES = ["optical"]


DEVICE_NAME_NETWORK_NUMBER_SUBSTITUTIONS = {
    "sn1": "227",
    "supernode1": "227",
    "375p": "227",
    "sn3": "713",
}

NETWORK_NUMBER_REGEX_FOR_DEVICE_NAME = r"\b\d{1,4}\b"

DEFAULT_SECTOR_AZIMUTH = 0  # decimal degrees (compass heading)
DEFAULT_SECTOR_WIDTH = 0  # decimal degrees
DEFAULT_SECTOR_RADIUS = 1  # km

# The guesses in this object are okay, since we will always communicate these guesses
# via a slack notification, giving admins a chance to update the data
DEVICE_MODEL_TO_BEAM_WIDTH = {
    "LAP-120": 120,
    "LAP-GPS": 120,
    "PS-5AC": 45,  # In reality this is based on the antenna used, this is just a guess based on our historical use
    "RP-5AC-Gen2": 90,  # In reality this is based on the antenna used, this is just a guess based on our historical use
}

# Controls how long a device can be offline in UISP for before we mark
# it as "Inactive" in meshdb
UISP_OFFLINE_DURATION_BEFORE_MARKING_INACTIVE = datetime.timedelta(days=30)

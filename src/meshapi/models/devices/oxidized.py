# Model IDs returned by oxidized_model() in the UISP-to-Oxidized inventory script.
# This list and its labels are frozen for migration 0015. Use a new snapshot for future changes.
DEVICE_TYPES = (
    "airfiber",
    "airos",
    "airos10",
    "apcaos",
    "cambiumepmp",
    "edgeos",
    "edgeswitch",
    "fastiron",
    "fsos",
    "ios",
    "iosxr",
    "junos",
    "nxos",
    "openwrt",
    "routeros",
    "siklu",
    "swos",
    "unifiap",
    "other",
)

DEVICE_TYPE_CHOICES = tuple(
    (device_type, "Other" if device_type == "other" else device_type) for device_type in DEVICE_TYPES
)

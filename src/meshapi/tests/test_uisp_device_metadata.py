import pytest

from meshapi.util.uisp_import.device_metadata import backup_platform, management_ip


@pytest.mark.parametrize(
    ("identification", "expected"),
    [
        ({"vendor": "Siklu", "modelName": "EH-1200FX"}, "siklu"),
        ({"modelName": "ICX 7150"}, "fastiron"),
        ({"vendor": "Fiberstore", "type": "switch"}, "fsos"),
        ({"vendor": "MikroTik", "model": "CSS610"}, "swos"),
        ({"modelName": "Wave Nano"}, "airos10"),
        ({"name": "mesh-openwrt"}, "openwrt"),
        ({"modelName": "Juniper QFX"}, "junos"),
        ({"vendor": "Cisco", "platformName": "NX-OS"}, "nxos"),
        ({"vendor": "Cisco", "platformName": "IOS-XR"}, "iosxr"),
        ({"vendor": "Cisco", "modelName": "Catalyst"}, "ios"),
        ({"modelName": "Force 4625"}, "cambiumepmp"),
        ({"modelName": "Smart-UPS"}, "apcaos"),
        ({"modelName": "hEXs - RB760iGS"}, "routeros"),
        ({"modelName": "EdgeRouter X"}, "edgeos"),
        ({"modelName": "EdgeSwitch"}, "edgeswitch"),
        ({"modelName": "AF60"}, "airfiber"),
        ({"modelName": "UAP-AC"}, "unifiap"),
        ({"type": "airMax"}, "airos"),
        ({"modelName": "Wave MLO6", "platformName": "airOS 10"}, None),
        ({"modelName": "Wave AP Gen 2", "vendor": "Ubiquiti"}, None),
        ({"vendor": "Cisco"}, None),
        ({"vendor": "Siklu", "modelName": "MultiHaul TG"}, None),
        ({}, None),
    ],
)
def test_backup_platform(identification, expected):
    assert backup_platform(identification) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ({"ipAddress": "10.69.123.45", "meta": {"customIpAddress": "10.69.123.46"}}, "10.69.123.45"),
        ({"ipAddress": "169.254.1.1", "meta": {"customIpAddress": "10.69.123.45"}}, "10.69.123.45"),
        ({"ipAddress": "2001:db8::45", "ipAddressList": ["10.69.123.45"]}, "10.69.123.45"),
        ({"ipAddressList": ["0.0.0.0", "::1", "ff02::1", "[2001:0db8::45]"]}, "2001:db8::45"),
        ({"ipAddress": "10.69.123.256", "identification": {"ip": "10.69.123.45"}}, "10.69.123.45"),
        ({"ipAddressList": ["10.69.123.45/24", "224.0.0.1", None]}, None),
        ({}, None),
    ],
)
def test_management_ip(source, expected):
    assert management_ip({"identification": {}, **source}) == expected

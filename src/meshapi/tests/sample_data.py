from geopy import Location, Point

from meshapi.models import Device, Install, Node

sample_member = {
    "name": "John Smith",
    "primary_email_address": "john.smith@example.com",
    "phone_number": "+1 555-555-5555",
    "slack_handle": "@jsmith",
}

sample_building = {
    "bin": 8888,
    "street_address": "3333 Chom St",
    "city": "Brooklyn",
    "state": "NY",
    "zip_code": "11111",
    "latitude": 0.0,
    "longitude": 0.0,
    "altitude": 0.0,
    "address_truth_sources": ["NYCPlanningLabs"],
}


sample_node = {
    "name": "Amazing Node",
    "status": Node.NodeStatus.ACTIVE,
    "latitude": 0.0,
    "longitude": 0.0,
}

sample_device = {
    "status": Device.DeviceStatus.ACTIVE,
}

sample_install = {
    "status": Install.InstallStatus.ACTIVE,
    "ticket_number": "69",
    "request_date": "2022-02-27T00:00:00Z",
    "install_date": "2022-03-01",
    "abandon_date": "9999-01-01",
    "unit": "3",
    "roof_access": True,
    "notes": "Referral: Read about it on the internet",
}

sample_address_response = {
    "features": [
        {
            "geometry": {"coordinates": [-73.98492, 40.716245]},
            "properties": {
                "postalcode": 10002,
                "housenumber": "151",
                "street": "Broome St",
                "borough": "Manhattan",
                "region_a": "NY",
                "addendum": {"pad": {"bin": 1234}},
            },
        }
    ]
}


sample_osm_address_response = Location(
    "151, Broome Street, Manhattan Community Board 3, Manhattan, New York County, City of New York, New York, 10002, United States",
    Point(40.7162281, -73.98489654157149, 0.0),
    {
        "address": {
            "ISO3166-2-lvl4": "US-NY",
            "city": "City of New York",
            "country": "United States",
            "country_code": "us",
            "county": "New York County",
            "house_number": "151",
            "neighbourhood": "Manhattan Community Board 3",
            "postcode": "10002",
            "road": "Broome Street",
            "state": "New York",
            "suburb": "Manhattan",
        },
        "addresstype": "building",
        "boundingbox": ["40.7160582", "40.7164320", "-73.9852426", "-73.9847390"],
        "class": "building",
        "display_name": "151, Broome Street, Manhattan Community Board 3, Manhattan, New York County, City of New York, New York, 10002, United States",
        "importance": 9.175936522464359e-05,
        "lat": "40.7162281",
        "licence": "Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright",
        "lon": "-73.98489654157149",
        "name": "",
        "osm_id": 250268365,
        "osm_type": "way",
        "place_id": 333450671,
        "place_rank": 30,
        "type": "yes",
    },
)

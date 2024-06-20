from meshapi.models import Device, Install, Node

sample_member = {
    "name": "John Smith",
    "primary_email_address": "john.smith@example.com",
    "phone_number": "+1-555-555-5555",
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
    "model": "OmniTik",
    "status": Device.DeviceStatus.ACTIVE,
    "type": Device.DeviceType.AP,
    "latitude": 0.0,
    "longitude": 0.0,
}

sample_install = {
    "status": Install.InstallStatus.ACTIVE,
    "ticket_id": 69,
    "request_date": "2022-02-27",
    "install_date": "2022-03-01",
    "abandon_date": "9999-01-01",
    "building": 1,
    "unit": "3",
    "roof_access": True,
    "member": 1,
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

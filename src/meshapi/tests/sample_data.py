from meshapi.models import Install

sample_member = {
    "name": "John Smith",
    "email_address": "john.smith@example.com",
    "phone_number": "555-555-5555",
    "slack_handle": "@jsmith",
}

sample_building = {
    "bin": 8888,
    "building_status": 1,
    "street_address": "3333 Chom St",
    "city": "Brooklyn",
    "state": "NY",
    "zip_code": 11111,
    "latitude": 0.0,
    "longitude": 0.0,
    "altitude": 0.0,
    "primary_nn": 2000,
    "address_truth_sources": ["NYCPlanningLabs"],
}

sample_install = {
    "network_number": 2000,
    "install_status": Install.InstallStatus.ACTIVE,
    "ticket_id": 69,
    "request_date": "2022-02-27",
    "install_date": "2022-03-01",
    "abandon_date": None,
    "building": 1,
    "unit": 3,
    "roof_access": True,
    "member": 1,
    "notes": "Referral: Read about it on the internet",
}

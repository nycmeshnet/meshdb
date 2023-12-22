from meshapi.models import Install

sample_member = {
    "first_name": "John",
    "last_name": "Smith",
    "email_address": "john.smith@example.com",
    "phone_numer": "555-555-5555",
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
    "network_number": 9001,
    "install_date": "2222-02-02",
    "abandon_date": "",
}

sample_install = {
    "install_status": Install.InstallStatus.ACTIVE,
    "install_number": 420,
    "ticket_id": 69,
    "request_date": "2022-02-27",
    "install_date": "2022-03-01",
    "abandon_date": "",
    "building_id": 1,
    "unit": 3,
    "roof_access": True,
    "member_id": 1,
    "referral": "Read about it on the internet",
    "notes": "",
}

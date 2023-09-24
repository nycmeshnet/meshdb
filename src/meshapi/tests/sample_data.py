from meshapi.models import Install, Request

sample_member = {
    "id": 0,
    "first_name": "John",
    "last_name": "Smith",
    "email_address": "john.smith@example.com",
    "phone_numer": "555-555-5555",
    "slack_handle": "@jsmith",
}

sample_building = {
    "id": 0,
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
    "id": 0,
    "install_number": 420,
    "install_status": Install.InstallStatus.ACTIVE,
    "install_date": "2022-03-01",
    "abandon_date": "",
    "member_id": 0,
    "building_id": 0,
}

sample_request = {
    "id": 0,
    "request_status": Request.RequestStatus.OPEN,
    "ticket_id": 0,
    "member_id": 0,
    "building_id": 0,
    "install_id": "",
}

from meshapi.models import Building, Device, Install, Link, Member

sample_member = {
    "name": "John Smith",
    "primary_email_address": "john.smith@example.com",
    "phone_number": "555-555-5555",
    "slack_handle": "@jsmith",
}

sample_building = {
    "bin": 8888,
    "building_status": "Active",
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

sample_device = {
    "status": Device.DeviceStatus.ACTIVE,
    "name": "sample-device",
    "device_name": "Omni",
    "serves_install": 1,
    "powered_by_install": 1,
    "network_number": 2000,
}

sample_sector = {
    "status": Device.DeviceStatus.ACTIVE,
    "name": "sample-sector",
    "device_name": "LAP-120",
    "network_number": None,
    "powered_by_install": 1,
    "radius": 2.0,
    "azimuth": 180.0,
    "width": 90.0,
    "ssid": "sample-sector-ssid",
}


# Utility class to lessen the toil of setting up tests
def add_sample_data():
    sample_install_copy = sample_install.copy()
    building_1 = Building(**sample_building)
    building_1.save()
    sample_install_copy["building"] = building_1

    building_2 = Building(**sample_building)
    building_2.street_address = "69" + str(building_2.street_address)
    building_2.save()

    member = Member(**sample_member)
    member.save()
    sample_install_copy["member"] = member

    install_1 = Install(**sample_install_copy)
    install_1.save()

    install_2 = Install(**sample_install_copy)
    install_2.building = building_2
    install_2.save()

    device_1 = Device(
        id=1,
        name="Vernon",
        device_name="LBE",
        status="Active",
    )
    device_1.save()

    device_2 = Device(
        id=2,
        name="Not Vernon",
        device_name="LBE",
        status="Active",
    )
    device_2.save()

    link = Link(
        from_device=device_1,
        to_device=device_2,
        status=Link.LinkStatus.ACTIVE,
    )
    link.save()

    return member, building_1, building_2, install_1, install_2, device_1, device_2, link

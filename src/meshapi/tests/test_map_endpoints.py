import datetime
import json

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from rest_framework.authtoken.models import Token

from meshapi.models import Building, Device, Install, Link, Member, Sector
from meshapi.tests.test_kml_endpoint import create_building_install_pair


class TestViewsGetUnauthenticated(TestCase):
    c = Client()

    # def setUp(self) -> None:
    #

    def test_views_get_unauthenticated(self):
        routes = [
            ("/api/v1/mapdata/installs/", 200),
            ("/api/v1/mapdata/links/", 200),
            ("/api/v1/mapdata/sectors/", 200),
        ]

        for route, code in routes:
            response = self.c.get(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for GET {route}. Should be {code}, but got {response.status_code}",
            )

            response = self.c.options(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for OPTIONS {route}. Should be {code}, but got {response.status_code}",
            )

    def test_install_data(self):
        installs = []
        buildings = []
        devices = []

        # Use the same member for everything since it doesn't matter
        member = Member(name="Fake Name")
        member.save()

        buildings.append(
            Building(
                building_status=Building.BuildingStatus.INACTIVE,
                address_truth_sources="",
                latitude=40.7686554,
                longitude=-73.9291817,
                altitude=37,
            )
        )
        installs.append(
            Install(
                install_number=2,
                status=Install.InstallStatus.INACTIVE,
                request_date=datetime.date(2015, 3, 15),
                install_date=datetime.date(2021, 7, 25),
                roof_access=False,
                building=buildings[-1],
                member=member,
                notes="Spreadsheet notes:\nPeter",
            )
        )

        buildings.append(
            Building(
                building_status=Building.BuildingStatus.ACTIVE,
                address_truth_sources="",
                latitude=40.724868,
                longitude=-73.987881,
                altitude=27,
                site_name="Brian",
                primary_nn=3,
            )
        )
        installs.append(
            Install(
                install_number=3,
                status=Install.InstallStatus.ACTIVE,
                request_date=datetime.date(2015, 3, 15),
                install_date=datetime.date(2014, 10, 14),
                roof_access=False,
                building=buildings[-1],
                member=member,
                notes="Spreadsheet notes:\nHub: LiteBeamLR to SN1 plus kiosk failover",
            )
        )
        devices.append(
            Device(
                name="FakeDevice",
                device_name="LBE",
                status=Device.DeviceStatus.ACTIVE,
                network_number=3,
                serves_install=installs[-1],
                powered_by_install=installs[-1],
            )
        )
        #installs[-1].via_device.set(devices[-1])

        buildings.append(
            Building(
                building_status=Building.BuildingStatus.ACTIVE,
                address_truth_sources="",
                latitude=40.660073,
                longitude=-73.921184,
                altitude=16,
            )
        )
        installs.append(
            Install(
                install_number=190,
                status=Install.InstallStatus.REQUEST_RECEIVED,
                request_date=datetime.date(2015, 9, 30),
                roof_access=False,
                building=buildings[-1],
                member=member,
            )
        )

        buildings.append(
            Building(
                building_status=Building.BuildingStatus.ACTIVE,
                address_truth_sources="",
                latitude=40.6962265,
                longitude=-73.9917741,
                altitude=66,
            )
        )
        installs.append(
            Install(
                install_number=14956,
                status=Install.InstallStatus.PENDING,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )

        buildings.append(
            Building(
                building_status=Building.BuildingStatus.ACTIVE,
                address_truth_sources="",
                latitude=40.6962265,
                longitude=-73.9917741,
                altitude=66,
            )
        )
        installs.append(
            Install(
                install_number=245,
                status=Install.InstallStatus.NN_REASSIGNED,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )

        buildings.append(
            Building(
                building_status=Building.BuildingStatus.ACTIVE,
                address_truth_sources="",
                latitude=40.6962265,
                longitude=-73.9917741,
                altitude=66,
                primary_nn=567,
            )
        )
        installs.append(
            Install(
                install_number=15657,
                status=Install.InstallStatus.ACTIVE,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )
        devices.append(
            Device(
                name="FakeDevice2",
                device_name="LBE",
                status=Device.DeviceStatus.ACTIVE,
                network_number=567,
                serves_install=installs[-1],
                powered_by_install=installs[-1],
            )
        )
        #installs[-1].via_device.set(devices[-1])

        installs.append(
            Install(
                install_number=2134,
                status=Install.InstallStatus.CLOSED,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )

        for building in buildings:
            building.save()

        for install in installs:
            install.save()

        for device in devices:
            device.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/mapdata/installs/")

        self.assertEqual(
            json.loads(response.content.decode("UTF8")),
            [
                {
                    "id": 2,
                    "status": "Powered Off",
                    "coordinates": [-73.9291817, 40.7686554, 37.0],
                    "requestDate": 1426377600000,
                    "installDate": 1627171200000,
                    "roofAccess": False,
                    "notes": "Peter",
                    "panoramas": [],
                },
                {
                    "id": 3,
                    "name": "Brian",
                    "status": "Installed",
                    "coordinates": [-73.987881, 40.724868, 27.0],
                    "requestDate": 1426377600000,
                    "installDate": 1413244800000,
                    "roofAccess": False,
                    "notes": "Hub: LiteBeamLR to SN1 plus kiosk failover",
                    "panoramas": [],
                },
                {
                    "id": 190,
                    "coordinates": [-73.921184, 40.660073, 16.0],
                    "requestDate": 1443571200000,
                    "roofAccess": False,
                    "panoramas": [],
                },
                {
                    "id": 567,
                    "status": "NN Assigned",
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
                    "requestDate": 1706313600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
                {
                    "id": 14956,
                    "status": "Interested",
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
                    "requestDate": 1706313600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
                {
                    "id": 15657,
                    "status": "Installed",
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
                    "requestDate": 1706313600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
            ],
        )

    def test_sector_data(self):
        sectors = []
        buildings = []

        # Use the same member for everything since it doesn't matter
        member = Member(name="Fake Name")
        member.save()

        buildings.append(
            Building(
                building_status=Building.BuildingStatus.ACTIVE,
                address_truth_sources="",
                latitude=0,
                longitude=0,
                altitude=0,
                primary_nn=155,
            )
        )
        sectors.append(
            Sector(
                building=buildings[-1],
                radius=0.3,
                azimuth=0,
                width=360,
                status=Sector.SectorStatus.ACTIVE,
                device_name="Omni",
                install_date=datetime.date(2021, 3, 21),
            )
        )
        buildings.append(
            Building(
                building_status=Building.BuildingStatus.ACTIVE,
                address_truth_sources="",
                latitude=0,
                longitude=0,
                altitude=0,
                primary_nn=227,
            )
        )
        sectors.append(
            Sector(
                building=buildings[-1],
                radius=0.75,
                azimuth=300,
                width=90,
                status=Sector.SectorStatus.ABANDONED,
                device_name="SN1Sector2",
            )
        )
        buildings.append(
            Building(
                building_status=Building.BuildingStatus.ACTIVE,
                address_truth_sources="",
                latitude=0,
                longitude=0,
                altitude=0,
            )
        )
        sectors.append(
            Sector(
                building=buildings[-1],
                radius=0.3,
                azimuth=0,
                width=360,
                status=Sector.SectorStatus.POTENTIAL,
                device_name="Omni",
            )
        )

        for building in buildings:
            building.save()

        for sector in sectors:
            sector.save()

        install = Install(
            install_number=1126,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 9, 30),
            roof_access=False,
            building=buildings[-1],
            member=member,
        )
        install.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/mapdata/sectors/")

        self.assertEqual(
            json.loads(response.content.decode("UTF8")),
            [
                {
                    "nodeId": 155,
                    "radius": 0.3,
                    "azimuth": 0,
                    "width": 360,
                    "status": "active",
                    "device": "Omni",
                    "installDate": 1616284800000,
                },
                {
                    "nodeId": 1126,
                    "radius": 0.3,
                    "azimuth": 0,
                    "width": 360,
                    "status": "potential",
                    "device": "Omni",
                },
            ],
        )

    def test_link_data(self):
        links = []

        grand, grand_inst, grand_device = create_building_install_pair(None, 1934, Building.BuildingStatus.ACTIVE)
        grand.save()
        grand_inst.save()
        grand_device.save()

        sn1, sn1_inst, sn1_device = create_building_install_pair(None, 227, Building.BuildingStatus.ACTIVE)
        sn1.save()
        sn1_inst.save()
        sn1_device.save()

        sn10, sn10_inst, sn10_device = create_building_install_pair(None, 10, Building.BuildingStatus.ACTIVE)
        sn10.save()
        sn10_inst.save()
        sn10_device.save()

        sn3, sn3_inst, sn3_device = create_building_install_pair(None, 713, Building.BuildingStatus.ACTIVE)
        sn3.save()
        sn3_inst.save()
        sn3_device.save()


        brian, brian_inst, brian_device = create_building_install_pair(None, 3, Building.BuildingStatus.ACTIVE)
        brian.save()
        brian_inst.save()
        brian_device.save()

        random, random_inst, random_device = create_building_install_pair(None, 123, Building.BuildingStatus.ACTIVE)
        random.save()
        random_inst.save()
        random_device.save()

        inactive, inactive_inst, inactive_device = create_building_install_pair(None, 123456, Building.BuildingStatus.INACTIVE)
        inactive_device.status = Device.DeviceStatus.ABANDONED
        inactive.save()
        inactive_inst.save()
        inactive_device.save()

        links.append(
            Link(
                from_device=sn1_device,
                to_device=sn3_device,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.VPN,
                install_date=datetime.date(2022, 1, 26),
            )
        )

        links.append(
            Link(
                from_device=sn1_device,
                to_device=grand_device,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.MMWAVE,
            )
        )

        links.append(
            Link(
                from_device=sn1_device,
                to_device=brian_device,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=grand_device,
                to_device=sn10_device,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIBER,
            )
        )

        links.append(
            Link(
                from_device=grand_device,
                to_device=random_device,
                status=Link.LinkStatus.PLANNED,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=sn1_device,
                to_device=random_device,
                status=Link.LinkStatus.DEAD,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=sn1_device,
                to_device=inactive_device,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        for link in links:
            link.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/mapdata/links/")

        self.assertEqual(
            json.loads(response.content.decode("UTF8")),
            [
                {
                    "from": 227,
                    "to": 713,
                    "status": "vpn",
                    "installDate": 1643155200000,
                },
                {
                    "from": 227,
                    "to": 1934,
                    "status": "60GHz",
                },
                {
                    "from": 227,
                    "to": 3,
                    "status": "active",
                },
                {
                    "from": 1934,
                    "to": 10,
                    "status": "fiber",
                },
                {
                    "from": 1934,
                    "to": 123,
                    "status": "planned",
                },
            ],
        )

    def test_link_install_number_resolution(self):
        links = []

        # Use the same member for everything since it doesn't matter
        member = Member(name="Fake Name")
        member.save()

        building_1 = Building(
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            primary_nn=555,
        )
        building_1.save()

        Install(
            install_number=5,
            status=Install.InstallStatus.INACTIVE,
            request_date=datetime.date(2015, 3, 15),
            building=building_1,
            member=member,
        ).save()
        Install(
            install_number=6,
            status=Install.InstallStatus.CLOSED,
            request_date=datetime.date(2015, 3, 15),
            building=building_1,
            member=member,
        ).save()
        Install(
            install_number=7,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            building=building_1,
            member=member,
        ).save()

        building_2 = Building(
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            primary_nn=99,
        )
        building_2.save()
        Install(
            install_number=90,
            status=Install.InstallStatus.CLOSED,
            request_date=datetime.date(2015, 3, 15),
            building=building_2,
            member=member,
        ).save()
        Install(
            install_number=91,
            status=Install.InstallStatus.NN_REASSIGNED,
            request_date=datetime.date(2015, 3, 15),
            building=building_2,
            member=member,
        ).save()

        building_3 = Building(
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            primary_nn=731,
        )
        building_3.save()
        Install(
            install_number=104,
            status=Install.InstallStatus.PENDING,
            request_date=datetime.date(2015, 3, 15),
            building=building_3,
            member=member,
        ).save()
        Install(
            install_number=105,
            status=Install.InstallStatus.REQUEST_RECEIVED,
            request_date=datetime.date(2015, 3, 15),
            building=building_3,
            member=member,
        ).save()

        links.append(
            Link(
                from_device=building_1,
                to_device=building_2,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=building_2,
                to_device=building_3,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=building_3,
                to_device=building_1,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        for link in links:
            link.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/mapdata/links/")

        self.assertEqual(
            json.loads(response.content.decode("UTF8")),
            [
                {
                    "from": 7,
                    "to": 99,
                    "status": "active",
                },
                {
                    "from": 99,
                    "to": 104,
                    "status": "active",
                },
                {
                    "from": 104,
                    "to": 7,
                    "status": "active",
                },
            ],
        )

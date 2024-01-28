import datetime
import json

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from rest_framework.authtoken.models import Token

from meshapi.models import Building, Install, Link, Member, Sector


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
                install_status=Install.InstallStatus.INACTIVE,
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
                node_name="Brian",
            )
        )
        installs.append(
            Install(
                install_number=3,
                install_status=Install.InstallStatus.ACTIVE,
                request_date=datetime.date(2015, 3, 15),
                install_date=datetime.date(2014, 10, 14),
                roof_access=False,
                building=buildings[-1],
                member=member,
                notes="Spreadsheet notes:\nHub: LiteBeamLR to SN1 plus kiosk failover",
            )
        )

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
                install_status=Install.InstallStatus.NN_ASSIGNED,
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
                install_status=Install.InstallStatus.OPEN,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )

        installs.append(
            Install(
                install_number=2134,
                install_status=Install.InstallStatus.CLOSED,
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
                    "status": "NN assigned",
                    "coordinates": [-73.921184, 40.660073, 16],
                    "requestDate": 1443571200000,
                    "roofAccess": False,
                    "panoramas": [],
                },
                {
                    "id": 14956,
                    "coordinates": [-73.9917741, 40.6962265, 66],
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
            install_status=Install.InstallStatus.ACTIVE,
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
                    "nodeId": 227,
                    "radius": 0.75,
                    "azimuth": 300,
                    "width": 90,
                    "status": "abandoned",
                    "device": "SN1Sector2",
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

        grand = Building(
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            primary_nn=1934,
        )
        grand.save()

        sn1 = Building(
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            primary_nn=227,
        )
        sn1.save()

        sn10 = Building(
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            primary_nn=10,
        )
        sn10.save()

        sn3 = Building(
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            primary_nn=713,
        )
        sn3.save()

        brian = Building(
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            primary_nn=3,
        )
        brian.save()

        random = Building(
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            primary_nn=123,
        )
        random.save()

        links.append(
            Link(
                from_building=sn1,
                to_building=sn3,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.VPN,
                install_date=datetime.date(2022, 1, 26),
            )
        )

        links.append(
            Link(
                from_building=sn1,
                to_building=grand,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.MMWAVE,
            )
        )

        links.append(
            Link(
                from_building=sn1,
                to_building=brian,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_building=grand,
                to_building=sn10,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIBER,
            )
        )

        links.append(
            Link(
                from_building=grand,
                to_building=random,
                status=Link.LinkStatus.PLANNED,
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

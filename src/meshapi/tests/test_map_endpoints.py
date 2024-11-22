import datetime
import json
import uuid

import requests_mock
from django.test import Client, TestCase

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector
from meshapi.serializers import MapDataLinkSerializer
from meshapi.tests.sample_kiosk_data import SAMPLE_OPENDATA_NYC_LINKNYC_KIOSK_RESPONSE
from meshapi.views import LINKNYC_KIOSK_DATA_URL


class TestViewsGetUnauthenticated(TestCase):
    c = Client()

    def test_views_get_unauthenticated(self):
        routes = [
            ("/api/v1/mapdata/nodes/", 200),
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
        nodes = []

        # Use the same member for everything since it doesn't matter
        member = Member(name="Fake Name")
        member.save()

        buildings.append(
            Building(
                address_truth_sources=[],
                latitude=40.7686554,
                longitude=-73.9291817,
                altitude=37,
                panoramas=["https://node-db.netlify.app/panoramas/2.jpg"],
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

        nodes.append(
            Node(
                network_number=3,
                name="Brian",
                status=Node.NodeStatus.ACTIVE,
                latitude=40.724868,
                longitude=-73.987881,
                type=Node.NodeType.HUB,
            )
        )
        buildings.append(
            Building(
                address_truth_sources=[],
                latitude=40.724868,
                longitude=-73.987881,
                altitude=27,
                primary_node=nodes[-1],
                panoramas=[
                    "https://node-db.netlify.app/panoramas/3.jpg",
                    "https://node-db.netlify.app/panoramas/3a.jpg",
                    "https://node-db.netlify.app/panoramas/3b.jpg",
                ],
            )
        )
        installs.append(
            Install(
                install_number=3,
                node=nodes[-1],
                status=Install.InstallStatus.ACTIVE,
                request_date=datetime.date(2015, 3, 15),
                install_date=datetime.date(2014, 10, 14),
                roof_access=False,
                building=buildings[-1],
                member=member,
                notes="Spreadsheet notes:\nHub: LiteBeamLR to SN1 plus kiosk failover",
            )
        )

        installs.append(
            Install(
                install_number=17232,
                node=nodes[-1],
                status=Install.InstallStatus.ACTIVE,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )

        nodes.append(
            Node(
                name="Potential Hub ABC",
                status=Node.NodeStatus.PLANNED,
                latitude=40.724868,
                longitude=-73.987881,
                type=Node.NodeType.HUB,
            )
        )
        buildings.append(
            Building(
                address_truth_sources=[],
                latitude=40.724868,
                longitude=-73.987881,
                altitude=27,
                primary_node=nodes[-1],
                panoramas=[],
            )
        )
        installs.append(
            Install(
                install_number=19452,
                node=nodes[-1],
                status=Install.InstallStatus.REQUEST_RECEIVED,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )
        installs.append(
            Install(
                install_number=19453,
                node=nodes[-1],
                status=Install.InstallStatus.REQUEST_RECEIVED,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )

        ap = AccessPoint(
            id=123456,
            node=nodes[-1],
            name="Northwest AP",
            install_date=datetime.date(2024, 1, 27),
            status=Device.DeviceStatus.ACTIVE,
            latitude=40.724863,
            longitude=-73.987879,
        )
        ap.save()

        buildings.append(
            Building(
                address_truth_sources=[],
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
                address_truth_sources=[],
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
                address_truth_sources=[],
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

        nodes.append(
            Node(
                network_number=567,
                name="Fancy Node",
                status=Node.NodeStatus.PLANNED,
                latitude=40.724868,
                longitude=-73.987881,
            )
        )
        buildings.append(
            Building(
                address_truth_sources=[],
                latitude=40.6962265,
                longitude=-73.9917741,
                altitude=66,
                primary_node=nodes[-1],
            )
        )
        installs.append(
            Install(
                install_number=15657,
                node=nodes[-1],
                status=Install.InstallStatus.REQUEST_RECEIVED,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )

        nodes.append(
            Node(
                network_number=888,
                status=Node.NodeStatus.ACTIVE,
                latitude=40.724868,
                longitude=-73.987881,
            )
        )
        buildings.append(
            Building(
                address_truth_sources=[],
                latitude=40.6962265,
                longitude=-73.9917741,
                altitude=66,
                primary_node=nodes[-1],
            )
        )
        installs.append(
            Install(
                install_number=1234,
                node=nodes[-1],
                status=Install.InstallStatus.ACTIVE,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )

        nodes.append(
            Node(
                network_number=1234,
                status=Node.NodeStatus.ACTIVE,
                latitude=40.724868,
                longitude=-73.987881,
            )
        )
        buildings.append(
            Building(
                address_truth_sources=[],
                latitude=40.6962265,
                longitude=-73.9917741,
                altitude=66,
                primary_node=nodes[-1],
            )
        )
        installs.append(
            Install(
                install_number=9999,
                node=nodes[-1],
                status=Install.InstallStatus.ACTIVE,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                member=member,
            )
        )

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

        nodes.append(
            Node(
                network_number=9823,
                status=Node.NodeStatus.ACTIVE,
                latitude=40.724868,
                longitude=-73.987881,
            )
        )
        installs.append(
            Install(
                install_number=12381924,
                status=Install.InstallStatus.PENDING,
                request_date=datetime.date(2024, 1, 27),
                roof_access=True,
                building=buildings[-1],
                node=nodes[-1],
                member=member,
            )
        )

        nodes.append(
            Node(
                network_number=9821,
                status=Node.NodeStatus.ACTIVE,
                latitude=40.724868,
                longitude=-73.987881,
            )
        )

        buildings.append(
            Building(
                address_truth_sources=[],
                latitude=40.6962265,
                longitude=-73.9917741,
                altitude=66,
                primary_node=nodes[-1],
            )
        )

        nodes.append(
            Node(
                network_number=9820,
                status=Node.NodeStatus.ACTIVE,
                latitude=40.724868,
                longitude=-73.987881,
            )
        )

        for node in nodes:
            node.save()

        for building in buildings:
            building.save()

        for install in installs:
            install.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/mapdata/nodes/")

        self.assertEqual(
            json.loads(response.content.decode("UTF8")),
            [
                {
                    "id": 2,
                    "status": "Powered Off",
                    "coordinates": [-73.9291817, 40.7686554, 37.0],
                    "requestDate": 1426392000000,
                    "installDate": 1627185600000,
                    "roofAccess": False,
                    "panoramas": ["2.jpg"],
                },
                {
                    "id": 3,
                    "name": "Brian",
                    "status": "Installed",
                    "coordinates": [-73.987881, 40.724868, None],
                    "requestDate": 1426392000000,
                    "installDate": 1413259200000,
                    "roofAccess": False,
                    "notes": "Hub",
                    "panoramas": ["3.jpg", "3a.jpg", "3b.jpg"],
                },
                {
                    "id": 190,
                    "coordinates": [-73.921184, 40.660073, 16.0],
                    "requestDate": 1443585600000,
                    "roofAccess": False,
                    "panoramas": [],
                },
                {
                    "id": 567,
                    "name": "Fancy Node",
                    "coordinates": [-73.987881, 40.724868, None],
                    "requestDate": 1706331600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
                {
                    "id": 888,
                    "status": "NN assigned",
                    "coordinates": [-73.987881, 40.724868, None],
                    "requestDate": 1706331600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
                {
                    "id": 1234,
                    "status": "Installed",
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
                    "requestDate": 1706331600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
                {
                    "coordinates": [-73.987881, 40.724868, None],
                    "id": 9820,
                    "panoramas": [],
                    "requestDate": None,
                    "roofAccess": True,
                    "status": "NN assigned",
                },
                {
                    "coordinates": [-73.987881, 40.724868, None],
                    "id": 9821,
                    "panoramas": [],
                    "requestDate": None,
                    "roofAccess": True,
                    "status": "NN assigned",
                },
                {
                    "coordinates": [-73.987881, 40.724868, None],
                    "id": 9823,
                    "panoramas": [],
                    "requestDate": 1706331600000,
                    "roofAccess": True,
                    "status": "NN assigned",
                },
                {
                    "id": 9999,
                    "status": "Installed",
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
                    "requestDate": 1706331600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
                {
                    "id": 14956,
                    "status": "Interested",
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
                    "requestDate": 1706331600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
                {
                    "id": 15657,
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
                    "requestDate": 1706331600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
                {
                    "id": 17232,
                    "coordinates": [-73.987881, 40.724868, 27.0],
                    "requestDate": 1706331600000,
                    "status": "Installed",
                    "panoramas": ["3.jpg", "3a.jpg", "3b.jpg"],
                    "roofAccess": True,
                },
                {
                    "id": 19452,
                    "coordinates": [-73.987881, 40.724868, None],
                    "requestDate": 1706331600000,
                    "name": "Potential Hub ABC",
                    "notes": "Hub",
                    "panoramas": [],
                    "roofAccess": True,
                },
                {
                    "id": 19453,
                    "coordinates": [-73.987881, 40.724868, 27.0],
                    "requestDate": 1706331600000,
                    "panoramas": [],
                    "roofAccess": True,
                },
                {
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
                    "id": 12381924,
                    "panoramas": [],
                    "requestDate": 1706331600000,
                    "roofAccess": True,
                    "status": "Interested",
                },
                {
                    "id": 1123456,
                    "name": "Northwest AP",
                    "status": "Installed",
                    "coordinates": [-73.987879, 40.724863, None],
                    "requestDate": 1706331600000,
                    "installDate": 1706331600000,
                    "roofAccess": False,
                    "notes": "AP",
                    "panoramas": [],
                },
            ],
        )

    def test_sector_data(self):
        sectors = []
        nodes = []

        # Use the same member for everything since it doesn't matter
        member = Member(name="Fake Name")
        member.save()

        fake_building = Building(address_truth_sources=[], latitude=0, longitude=0)
        fake_building.save()

        nodes.append(
            Node(
                network_number=155,
                latitude=0,
                longitude=0,
                status=Node.NodeStatus.ACTIVE,
            )
        )
        sectors.append(
            Sector(
                node=nodes[-1],
                radius=0.3,
                azimuth=0,
                width=360,
                status=Device.DeviceStatus.ACTIVE,
                install_date=datetime.date(2021, 3, 21),
            )
        )
        nodes.append(
            Node(
                network_number=227,
                latitude=0,
                longitude=0,
                status=Node.NodeStatus.ACTIVE,
            )
        )
        sectors.append(
            Sector(
                node=nodes[-1],
                radius=0.75,
                azimuth=300,
                width=90,
                status=Device.DeviceStatus.INACTIVE,
            )
        )

        nodes.append(
            Node(
                network_number=786,
                latitude=0,
                longitude=0,
                status=Node.NodeStatus.ACTIVE,
            )
        )
        sectors.append(
            Sector(
                node=nodes[-1],
                radius=0.3,
                azimuth=0,
                width=360,
                status=Device.DeviceStatus.POTENTIAL,
            )
        )

        for building in nodes:
            building.save()

        for sector in sectors:
            sector.save()

        install = Install(
            install_number=1126,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 9, 30),
            roof_access=False,
            building=fake_building,
            node=nodes[-1],
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
                    "installDate": 1616299200000,
                },
                {
                    "nodeId": 786,
                    "radius": 0.3,
                    "azimuth": 0,
                    "width": 360,
                    "status": "potential",
                },
            ],
        )

    def test_link_data(self):
        links = []

        member = Member(
            id=uuid.UUID("f0128b91-dbc6-466b-a030-298e39eb4733"),
            name="Fake Name",
        )
        member.save()

        grand = Node(
            id=uuid.UUID("ffa22d49-d99d-480f-a872-569f3bb8b5fb"),
            network_number=1934,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        grand.save()
        grand_omni = Device(
            id=uuid.UUID("e8b87c95-fe52-4ee6-8ea6-682d4f838861"),
            node=grand,
            status=Device.DeviceStatus.ACTIVE,
        )
        grand_omni.save()

        sn1 = Node(
            id=uuid.UUID("23d4acb4-43fc-4832-9ddd-219c12bdbc28"),
            network_number=227,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn1.save()

        sn1_building = Building(
            id=uuid.UUID("2ea7d857-3ade-42c6-92f1-18e30cd7c934"),
            address_truth_sources=[],
            latitude=0,
            longitude=0,
            primary_node=sn1,
        )
        sn1_building.save()

        sn1_install = Install(
            id=uuid.UUID("1fc94b13-6eaa-46a8-898b-44894bbd70dd"),
            member=member,
            install_number=227,
            building=sn1_building,
            node=sn1,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
        )
        sn1_install.save()

        sn1_omni = Device(
            id=uuid.UUID("116368d5-2437-4cfb-9d25-540533c8bfec"),
            node=sn1,
            status=Device.DeviceStatus.ACTIVE,
        )
        sn1_omni.save()

        sn10 = Node(
            id=uuid.UUID("e3919c3e-2a96-46f6-8941-b29875c8664c"),
            network_number=10,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn10.save()
        sn10_omni = Device(
            id=uuid.UUID("0f1259af-1cd0-471d-9294-7dbfac9cb6a9"),
            node=sn10,
            status=Device.DeviceStatus.ACTIVE,
        )
        sn10_omni.save()

        sn3 = Node(
            id=uuid.UUID("75e771be-d4cc-4ea2-bb48-4c8c83720822"),
            network_number=713,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        sn3.save()
        sn3_omni = Device(
            id=uuid.UUID("e8ce0468-e6c2-467c-92a4-97e1759ce35a"),
            node=sn3,
            status=Device.DeviceStatus.ACTIVE,
        )
        sn3_omni.save()

        sn3_building = Building(
            id=uuid.UUID("fd768f67-75a0-444f-a18d-c4faa09359b6"),
            address_truth_sources=[],
            latitude=0,
            longitude=0,
            primary_node=sn3,
        )
        sn3_building.save()

        sn3_install = Install(
            id=uuid.UUID("6b45c3a4-d9e2-4919-b415-0b1a6f6d27e5"),
            member=member,
            install_number=713,
            building=sn3_building,
            node=sn3,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
        )
        sn3_install.save()

        brian = Node(
            id=uuid.UUID("e7e3432e-eaee-403d-b400-5ddd8bd2e75b"),
            network_number=3,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        brian.save()
        brian_omni = Device(
            id=uuid.UUID("cc3ee525-d32b-4fa6-8b40-abc5babfd342"),
            node=brian,
            status=Device.DeviceStatus.ACTIVE,
        )
        brian_omni.save()

        random = Node(
            id=uuid.UUID("efe899b4-6a0c-4e28-8b1b-2d28669463cd"),
            network_number=123,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        random.save()
        random_building = Building(
            id=uuid.UUID("9b5ae47b-4525-4b0f-92b5-637b20341e0b"),
            latitude=0,
            longitude=0,
            address_truth_sources=[],
            primary_node=random,
        )
        random_building.save()
        random_install = Install(
            id=uuid.UUID("89b821a4-9aee-40d3-bfbf-a61785e1530a"),
            install_number=123,
            building=random_building,
            node=random,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            member=member,
        )
        random_install.save()
        random.save()
        random_omni = Device(
            id=uuid.UUID("a6106205-8d04-4a52-b3af-f0ffc1b84fcc"),
            node=random,
            status=Device.DeviceStatus.ACTIVE,
        )
        random_omni.save()

        random_addl_building = Building(
            id=uuid.UUID("adf61d61-5f69-42e6-b625-c7c6485fed80"),
            latitude=0,
            longitude=0,
            address_truth_sources=[],
            primary_node=random,
        )
        random_addl_building.save()

        random_addl_install = Install(
            id=uuid.UUID("f7f95143-e8f9-418e-9210-0b9718dfe884"),
            install_number=56789,
            building=random_addl_building,
            node=random,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            member=member,
        )
        random_addl_install.save()

        random_addl_install_2 = Install(
            id=uuid.UUID("05b1bce9-8c9d-4366-9eab-700073ba5f69"),
            install_number=56790,
            building=random_addl_building,
            node=random,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            member=member,
        )
        random_addl_install_2.save()

        random_addl_building_inactive = Building(
            id=uuid.UUID("f139a043-da80-46d4-a50d-03e200730b42"),
            latitude=0,
            longitude=0,
            address_truth_sources=[],
            primary_node=random,
        )
        random_addl_building_inactive.save()

        random_addl_install_inactive = Install(
            id=uuid.UUID("3522b840-8d20-4fd2-86e1-0d20db8a38f8"),
            install_number=56791,
            building=random_addl_building_inactive,
            node=random,
            status=Install.InstallStatus.INACTIVE,
            request_date=datetime.date(2015, 3, 15),
            member=member,
        )
        random_addl_install_inactive.save()

        inactive = Node(
            id=uuid.UUID("97c3fb73-e3f0-4eee-b1aa-d7a5bacd6122"),
            network_number=123456,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.INACTIVE,
        )
        inactive.save()
        inactive_omni = Device(
            id=uuid.UUID("3d33ef96-35fc-4703-8562-b154d701dbe6"),
            node=inactive,
            status=Device.DeviceStatus.ACTIVE,
        )
        inactive_omni.save()

        access_point_1 = AccessPoint(
            id=uuid.UUID("3caca726-f072-4faf-93c9-95e0b305393b"),
            node=grand,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
            altitude=0,
        )
        access_point_1.save()

        access_point_2 = AccessPoint(
            id=uuid.UUID("efe0b029-084e-427e-abb2-ac24c207a68c"),
            node=grand,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
            altitude=0,
        )
        access_point_2.save()

        links.append(
            Link(
                id=uuid.UUID("a8bf7b1f-99c8-4c41-8123-59eb12faaff3"),
                from_device=grand_omni,
                to_device=access_point_1,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.SIXTY_GHZ,
                install_date=datetime.date(2024, 1, 26),
            )
        )

        links.append(
            Link(
                id=uuid.UUID("0d1e7aaa-ada3-461d-b69d-fac439eb1778"),
                from_device=access_point_1,
                to_device=access_point_2,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.SIXTY_GHZ,
                install_date=datetime.date(2024, 1, 26),
            )
        )

        links.append(
            Link(
                id=uuid.UUID("d36b2c85-72fc-4f7f-a1f3-e642a6fefae1"),
                from_device=sn1_omni,
                to_device=sn3_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.VPN,
                install_date=datetime.date(2022, 1, 26),
            )
        )

        links.append(
            Link(
                id=uuid.UUID("2cd0c189-1b7d-4c2b-9530-f7eec74f28af"),
                from_device=sn1_omni,
                to_device=grand_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.SIXTY_GHZ,
            )
        )

        links.append(
            Link(
                id=uuid.UUID("d08c32d3-0909-4d62-8138-a1f7ce96d552"),
                from_device=sn1_omni,
                to_device=brian_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
            )
        )

        links.append(
            Link(
                id=uuid.UUID("56d45e5a-f880-4b97-893a-fa87189f23ab"),
                from_device=grand_omni,
                to_device=sn10_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIBER,
            )
        )

        links.append(
            Link(
                id=uuid.UUID("d85058c9-44d5-4e7b-9eff-062ead6b5869"),
                from_device=grand_omni,
                to_device=random_omni,
                status=Link.LinkStatus.PLANNED,
                type=Link.LinkType.FIVE_GHZ,
            )
        )

        links.append(
            Link(
                id=uuid.UUID("33986527-28a9-4146-bcd3-fee73034c45f"),
                from_device=sn1_omni,
                to_device=random_omni,
                status=Link.LinkStatus.INACTIVE,
                type=Link.LinkType.FIVE_GHZ,
            )
        )

        links.append(
            Link(
                id=uuid.UUID("76d35477-0497-46ea-b66d-eb61b59f63c5"),
                from_device=sn1_omni,
                to_device=inactive_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
            )
        )

        for link in links:
            link.save()

        modern_hub = Node(
            id=uuid.UUID("4e30718c-05e5-4ea6-999c-753d871c31c5"),
            network_number=413,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        modern_hub.save()

        modern_hub_building = Building(
            id=uuid.UUID("3e7c144d-6d7f-4f98-ab20-74ac26817781"),
            latitude=0,
            longitude=0,
            address_truth_sources=[],
            primary_node=modern_hub,
        )
        modern_hub_building.save()

        modern_hub_install = Install(
            id=uuid.UUID("729f80a3-1657-4a35-ad55-43dce7b69320"),
            install_number=123323,
            building=modern_hub_building,
            node=modern_hub,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            member=member,
        )
        modern_hub_install.save()

        potential_building = Building(
            id=uuid.UUID("d316be11-9199-40fa-819f-fb30fefa833f"),
            latitude=0,
            longitude=0,
            address_truth_sources=[],
        )
        potential_building.save()

        potential_install = Install(
            id=uuid.UUID("5d3ec95d-b5f2-4563-a9b5-be3f1525f6ac"),
            install_number=88892,
            building=potential_building,
            status=Install.InstallStatus.REQUEST_RECEIVED,
            request_date=datetime.date(2015, 3, 15),
            member=member,
        )
        potential_install.save()

        no_installs_building = Building(
            id=uuid.UUID("308d4701-0ad8-40a5-bc32-d42cec013808"),
            latitude=0,
            longitude=0,
            address_truth_sources=[],
        )
        no_installs_building.save()

        today = datetime.date.today()
        los = LOS(
            id=uuid.UUID("4dd407f0-4ec1-4c10-aeb6-a0be6c54bdd7"),
            from_building=random_building,
            to_building=potential_building,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=today,
        )
        los.save()

        los_duplicative = LOS(
            id=uuid.UUID("65545d65-4eab-481f-bc15-f4378285af97"),
            from_building=sn1_building,
            to_building=sn3_building,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=today,
        )
        los_duplicative.save()

        los_no_installs = LOS(
            id=uuid.UUID("e1ebf096-5d36-4a4b-b08c-b49b62aaeebd"),
            from_building=no_installs_building,
            to_building=random_building,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=today,
        )
        los_no_installs.save()

        modern_hub_los = LOS(
            id=uuid.UUID("655de0bf-28f0-4ec7-a85d-edcc432ed145"),
            from_building=modern_hub_building,
            to_building=potential_building,
            source=LOS.LOSSource.EXISTING_LINK,
            analysis_date=today,
        )
        modern_hub_los.save()

        modern_hub_los_duplicate = LOS(
            id=uuid.UUID("daa6ad4f-64d6-49dc-8df5-360525d4c3d0"),
            from_building=modern_hub_building,
            to_building=potential_building,
            source=LOS.LOSSource.EXISTING_LINK,
            analysis_date=today,
        )
        modern_hub_los_duplicate.save()

        self_loop_los = LOS(
            id=uuid.UUID("af8b485b-9b6f-47d9-a8c2-f2498de1c31e"),
            from_building=modern_hub_building,
            to_building=modern_hub_building,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=today,
        )
        self_loop_los.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/mapdata/links/")

        self.assertEqual(
            json.loads(response.content.decode("UTF8")),
            [
                {
                    "from": 227,
                    "to": 3,
                    "status": "active",
                },
                {
                    "from": 227,
                    "to": 713,
                    "status": "vpn",
                    "installDate": 1643173200000,
                },
                {
                    "from": 227,
                    "to": 1934,
                    "status": "60GHz",
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
                {
                    "from": 1934,
                    "installDate": 1706245200000,
                    "status": "60GHz",
                    "to": 1934,
                },
                {
                    "from": 56789,
                    "to": 123,
                    "status": "active",
                },
                {
                    "from": 123,
                    "to": 88892,
                    "status": "planned",
                },
                {
                    "from": 123323,
                    "to": 88892,
                    "status": "planned",
                },
                {
                    "from": 413,
                    "to": 88892,
                    "status": "planned",
                },
                {
                    "from": 1706171,
                    "status": "60GHz",
                    "to": 1150732,
                },
                {
                    "from": 1934,
                    "status": "60GHz",
                    "to": 1706171,
                },
            ],
        )

    def test_link_serializer_inactive_link(self):
        sn1 = Node(
            id=uuid.UUID("23d4acb4-43fc-4832-9ddd-219c12bdbc28"),
            network_number=227,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn1.save()

        sn1_omni = Device(
            id=uuid.UUID("116368d5-2437-4cfb-9d25-540533c8bfec"),
            node=sn1,
            status=Device.DeviceStatus.ACTIVE,
        )
        sn1_omni.save()

        random = Node(
            id=uuid.UUID("efe899b4-6a0c-4e28-8b1b-2d28669463cd"),
            network_number=123,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        random.save()

        random_omni = Device(
            id=uuid.UUID("a6106205-8d04-4a52-b3af-f0ffc1b84fcc"),
            node=random,
            status=Device.DeviceStatus.ACTIVE,
        )
        random_omni.save()

        inactive_link = Link(
            id=uuid.UUID("33986527-28a9-4146-bcd3-fee73034c45f"),
            from_device=sn1_omni,
            to_device=random_omni,
            status=Link.LinkStatus.INACTIVE,
            type=Link.LinkType.FIVE_GHZ,
        )

        self.assertEqual(
            MapDataLinkSerializer(inactive_link).data,
            {
                "from": 227,
                "to": 123,
                "status": "dead",
            },
        )

    def test_links_are_deduplicated(self):
        links = []

        member = Member(name="Fake Name")
        member.save()

        grand = Node(
            network_number=1934,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        grand.save()
        grand_omni = Device(
            node=grand,
            status=Device.DeviceStatus.ACTIVE,
        )
        grand_omni.save()
        grand_additional_device = Device(
            node=grand,
            status=Device.DeviceStatus.ACTIVE,
        )
        grand_additional_device.save()

        grand_building = Building(
            address_truth_sources=[],
            latitude=0,
            longitude=0,
            primary_node=grand,
        )
        grand_building.save()

        Install(
            install_number=1934,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            node=grand,
            member=member,
            building=grand_building,
        ).save()

        grand_node2 = Node(
            network_number=1938,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        grand_node2.save()
        grand2_omni = Device(
            node=grand_node2,
            status=Device.DeviceStatus.ACTIVE,
        )
        grand2_omni.save()

        grand_building2 = Building(
            address_truth_sources=[],
            latitude=0,
            longitude=0,
            primary_node=grand,
        )
        grand_building2.save()

        Install(
            install_number=1938,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            node=grand_node2,
            member=member,
            building=grand_building2,
        ).save()

        sn1 = Node(
            network_number=227,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn1.save()
        sn1_omni = Device(
            node=sn1,
            status=Device.DeviceStatus.ACTIVE,
        )
        sn1_omni.save()
        sn1_additional_device = Device(
            node=sn1,
            status=Device.DeviceStatus.ACTIVE,
        )
        sn1_additional_device.save()

        links.append(
            Link(
                id=uuid.UUID("1395f182-0b06-4a38-b7ed-26a1170f5f7f"),
                from_device=sn1_omni,
                to_device=grand_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.SIXTY_GHZ,
            )
        )
        links.append(
            Link(
                id=uuid.UUID("b2d6f7a8-7fe5-4d38-8d04-d0e14f3530e8"),
                from_device=sn1_additional_device,
                to_device=grand_additional_device,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
            )
        )
        links.append(
            Link(
                id=uuid.UUID("def40fc6-32cc-4c2a-8dac-4999b5306e6e"),
                from_device=grand2_omni,
                to_device=grand_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
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
                    "to": 1934,
                    "status": "60GHz",
                },
                {
                    "from": 1938,
                    "to": 1934,
                    "status": "active",
                },
            ],
        )

    def test_cable_run_links_to_invalid_nodes_are_not_created(self):
        links = []

        member = Member(name="Fake Name")
        member.save()

        grand = Node(
            network_number=1934,
            status=Node.NodeStatus.INACTIVE,
            latitude=0,
            longitude=0,
        )
        grand.save()
        grand_omni = Device(
            node=grand,
            status=Device.DeviceStatus.ACTIVE,
        )
        grand_omni.save()
        grand_additional_device = Device(
            node=grand,
            status=Device.DeviceStatus.ACTIVE,
        )
        grand_additional_device.save()

        grand_building = Building(
            address_truth_sources=[],
            latitude=0,
            longitude=0,
            primary_node=grand,
        )
        grand_building.save()

        Install(
            install_number=1934,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            node=grand,
            member=member,
            building=grand_building,
        ).save()

        grand_node2 = Node(
            network_number=1938,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        grand_node2.save()
        grand2_omni = Device(
            node=grand_node2,
            status=Device.DeviceStatus.ACTIVE,
        )
        grand2_omni.save()

        grand_building2 = Building(
            address_truth_sources=[],
            latitude=0,
            longitude=0,
            primary_node=grand,
        )
        grand_building2.save()

        Install(
            install_number=1938,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            node=grand_node2,
            member=member,
            building=grand_building2,
        ).save()

        for link in links:
            link.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/mapdata/links/")

        self.assertEqual(
            json.loads(response.content.decode("UTF8")),
            [],
        )

    def test_link_install_number_resolution(self):
        links = []

        # Use the same member & building for everything since it doesn't matter
        member = Member(name="Fake Name")
        member.save()

        fake_building = Building(address_truth_sources=[], latitude=0, longitude=0)
        fake_building.save()

        node_1 = Node(
            network_number=555,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        node_1.save()

        Install(
            install_number=5,
            status=Install.InstallStatus.INACTIVE,
            request_date=datetime.date(2015, 3, 15),
            node=node_1,
            member=member,
            building=fake_building,
        ).save()
        Install(
            install_number=6,
            status=Install.InstallStatus.CLOSED,
            request_date=datetime.date(2015, 3, 15),
            node=node_1,
            member=member,
            building=fake_building,
        ).save()
        Install(
            install_number=7,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            node=node_1,
            member=member,
            building=fake_building,
        ).save()

        node_2 = Node(
            network_number=99,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        node_2.save()
        Install(
            install_number=90,
            status=Install.InstallStatus.CLOSED,
            request_date=datetime.date(2015, 3, 15),
            node=node_2,
            member=member,
            building=fake_building,
        ).save()
        Install(
            install_number=91,
            status=Install.InstallStatus.NN_REASSIGNED,
            request_date=datetime.date(2015, 3, 15),
            node=node_2,
            member=member,
            building=fake_building,
        ).save()

        node_3 = Node(
            network_number=731,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        node_3.save()
        Install(
            install_number=104,
            status=Install.InstallStatus.PENDING,
            request_date=datetime.date(2015, 3, 15),
            node=node_3,
            member=member,
            building=fake_building,
        ).save()
        Install(
            install_number=105,
            status=Install.InstallStatus.REQUEST_RECEIVED,
            request_date=datetime.date(2015, 3, 15),
            node=node_3,
            member=member,
            building=fake_building,
        ).save()

        device_1 = Device(
            node=node_1,
            status=Device.DeviceStatus.ACTIVE,
        )
        device_1.save()
        device_2 = Device(
            node=node_2,
            status=Device.DeviceStatus.ACTIVE,
        )
        device_2.save()
        device_3 = Device(
            node=node_3,
            status=Device.DeviceStatus.ACTIVE,
        )
        device_3.save()

        links.append(
            Link(
                from_device=device_1,
                to_device=device_2,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
            )
        )

        links.append(
            Link(
                from_device=device_2,
                to_device=device_3,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
            )
        )

        links.append(
            Link(
                from_device=device_3,
                to_device=device_1,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
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
                    "from": 99,
                    "to": 731,
                    "status": "active",
                },
                {
                    "from": 555,
                    "to": 99,
                    "status": "active",
                },
                {
                    "from": 731,
                    "to": 555,
                    "status": "active",
                },
            ],
        )

    def test_install_number_used_for_links_with_no_nn(self):
        # Use the same member & building for everything since it doesn't matter
        member = Member(name="Fake Name")
        member.save()

        node1 = Node(
            name="Potential Hub ABC",
            status=Node.NodeStatus.PLANNED,
            latitude=40.724868,
            longitude=-73.987881,
            type=Node.NodeType.HUB,
        )
        node1.save()
        building1 = Building(
            address_truth_sources=[],
            latitude=40.724868,
            longitude=-73.987881,
            altitude=27,
            primary_node=node1,
            panoramas=[],
        )
        building1.save()
        install1 = Install(
            install_number=19452,
            node=node1,
            status=Install.InstallStatus.REQUEST_RECEIVED,
            request_date=datetime.date(2024, 1, 27),
            roof_access=True,
            building=building1,
            member=member,
        )
        install1.save()
        device1 = Device(
            node=node1,
            status=Device.DeviceStatus.ACTIVE,
        )
        device1.save()

        node2 = Node(
            network_number=123,
            status=Node.NodeStatus.PLANNED,
            latitude=40.724868,
            longitude=-73.987881,
            type=Node.NodeType.HUB,
        )
        node2.save()

        building2 = Building(
            address_truth_sources=[],
            latitude=40.724868,
            longitude=-73.987881,
            altitude=27,
            primary_node=node2,
            panoramas=[],
        )
        building2.save()
        install2 = Install(
            install_number=19459,
            node=node2,
            status=Install.InstallStatus.REQUEST_RECEIVED,
            request_date=datetime.date(2024, 1, 27),
            roof_access=True,
            building=building2,
            member=member,
        )
        install2.save()
        device2 = Device(
            node=node2,
            status=Device.DeviceStatus.ACTIVE,
        )
        device2.save()

        building3 = Building(
            address_truth_sources=[],
            latitude=40.724868,
            longitude=-73.987881,
            altitude=27,
            panoramas=[],
        )
        building3.save()
        install3 = Install(
            install_number=19460,
            status=Install.InstallStatus.REQUEST_RECEIVED,
            request_date=datetime.date(2024, 1, 27),
            roof_access=True,
            building=building3,
            member=member,
        )
        install3.save()

        link = Link(
            from_device=device1,
            to_device=device2,
            status=Link.LinkStatus.PLANNED,
            type=Link.LinkType.FIVE_GHZ,
        )
        link.save()
        los = LOS(
            from_building=building1,
            to_building=building3,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
        )
        los.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/mapdata/links/")

        self.assertEqual(
            json.loads(response.content.decode("UTF8")),
            [
                {
                    "from": 19452,
                    "to": 123,
                    "status": "planned",
                },
                {
                    "from": 19452,
                    "to": 19460,
                    "status": "planned",
                },
            ],
        )


class TestKiosk(TestCase):
    c = Client()

    @requests_mock.Mocker()
    def test_kiosk_list_good_state(self, city_api_call_request_mocker):
        city_api_call_request_mocker.get(LINKNYC_KIOSK_DATA_URL, json=SAMPLE_OPENDATA_NYC_LINKNYC_KIOSK_RESPONSE)

        response = self.c.get("/api/v1/mapdata/kiosks/")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(len(json.loads(response.content.decode("UTF8"))), 7)

    @requests_mock.Mocker()
    def test_kiosk_list_bad_fetch(self, city_api_call_request_mocker):
        city_api_call_request_mocker.get(LINKNYC_KIOSK_DATA_URL, status_code=500)

        response = self.c.get("/api/v1/mapdata/kiosks/")
        self.assertEqual(
            502,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(
            json.loads(response.content.decode("UTF8")), {"detail": "Error fetching data from City of New York"}
        )

    @requests_mock.Mocker()
    def test_kiosk_list_bad_response(self, city_api_call_request_mocker):
        bad_responses = [[], [{"blah": "abc"}]]

        for bad_response in bad_responses:
            city_api_call_request_mocker.get(LINKNYC_KIOSK_DATA_URL, json=bad_response)

            response = self.c.get("/api/v1/mapdata/kiosks/")
            self.assertEqual(
                502,
                response.status_code,
                f"status code incorrect, should be 200, but got {response.status_code}",
            )
            self.assertEqual(
                json.loads(response.content.decode("UTF8")),
                {"detail": "Invalid response received from City of New York"},
            )

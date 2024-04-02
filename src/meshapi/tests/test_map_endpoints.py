import datetime
import json

from django.test import Client, TestCase

from meshapi.models import Building, Device, Install, Link, Member, Node, Sector


class TestViewsGetUnauthenticated(TestCase):
    c = Client()

    # def setUp(self) -> None:
    #

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
        ap_device = Device(
            id=123456,
            node=nodes[-1],
            name="Northwest AP",
            model="Unknown",
            type=Device.DeviceType.AP,
            install_date=datetime.date(2024, 1, 27),
            status=Device.DeviceStatus.ACTIVE,
            latitude=40.724863,
            longitude=-73.987879,
        )
        ap_device.save()

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
                    "coordinates": [-73.987881, 40.724868, 27.0],
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
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
                    "requestDate": 1706331600000,
                    "roofAccess": True,
                    "panoramas": [],
                },
                {
                    "id": 888,
                    "status": "NN assigned",
                    "coordinates": [-73.9917741, 40.6962265, 66.0],
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
                latitude=0,
                longitude=0,
                radius=0.3,
                azimuth=0,
                width=360,
                status=Device.DeviceStatus.ACTIVE,
                model="Omni",
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
                latitude=0,
                longitude=0,
                radius=0.75,
                azimuth=300,
                width=90,
                status=Device.DeviceStatus.INACTIVE,
                model="LAP-120s",
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
                latitude=0,
                longitude=0,
                radius=0.3,
                azimuth=0,
                width=360,
                status=Device.DeviceStatus.POTENTIAL,
                model="Omni",
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
                    "device": "Omni",
                    "installDate": 1616299200000,
                },
                {
                    "nodeId": 786,
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
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        grand_omni.save()

        sn1 = Node(
            network_number=227,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn1.save()
        sn1_omni = Device(
            node=sn1,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn1_omni.save()

        sn10 = Node(
            network_number=10,
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn10.save()
        sn10_omni = Device(
            node=sn10,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn10_omni.save()

        sn3 = Node(
            network_number=713,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        sn3.save()
        sn3_omni = Device(
            node=sn3,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn3_omni.save()

        brian = Node(
            network_number=3,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        brian.save()
        brian_omni = Device(
            node=brian,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        brian_omni.save()

        random = Node(
            network_number=123,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.ACTIVE,
        )
        random.save()
        random_building = Building(
            latitude=0,
            longitude=0,
            address_truth_sources=[],
            primary_node=random,
        )
        random_building.save()
        random_install = Install(
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
            node=random,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        random_omni.save()

        random_addl_building = Building(
            latitude=0,
            longitude=0,
            address_truth_sources=[],
            primary_node=random,
        )
        random_addl_building.save()

        random_addl_install = Install(
            install_number=56789,
            building=random_addl_building,
            node=random,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            member=member,
        )
        random_addl_install.save()

        random_addl_install_2 = Install(
            install_number=56790,
            building=random_addl_building,
            node=random,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date(2015, 3, 15),
            member=member,
        )
        random_addl_install_2.save()

        random_addl_building_inactive = Building(
            latitude=0,
            longitude=0,
            address_truth_sources=[],
            primary_node=random,
        )
        random_addl_building_inactive.save()

        random_addl_install_inactive = Install(
            install_number=56791,
            building=random_addl_building_inactive,
            node=random,
            status=Install.InstallStatus.INACTIVE,
            request_date=datetime.date(2015, 3, 15),
            member=member,
        )
        random_addl_install_inactive.save()

        inactive = Node(
            network_number=123456,
            latitude=0,
            longitude=0,
            status=Node.NodeStatus.INACTIVE,
        )
        inactive.save()
        inactive_omni = Device(
            node=inactive,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        inactive_omni.save()

        links.append(
            Link(
                from_device=sn1_omni,
                to_device=sn3_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.VPN,
                install_date=datetime.date(2022, 1, 26),
            )
        )

        links.append(
            Link(
                from_device=sn1_omni,
                to_device=grand_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.MMWAVE,
            )
        )

        links.append(
            Link(
                from_device=sn1_omni,
                to_device=brian_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=grand_omni,
                to_device=sn10_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIBER,
            )
        )

        links.append(
            Link(
                from_device=grand_omni,
                to_device=random_omni,
                status=Link.LinkStatus.PLANNED,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=sn1_omni,
                to_device=random_omni,
                status=Link.LinkStatus.INACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=sn1_omni,
                to_device=inactive_omni,
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
                    "installDate": 1643173200000,
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
                {
                    "from": 56789,
                    "to": 123,
                    "status": "active",
                },
            ],
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
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        grand_omni.save()
        grand_additional_device = Device(
            node=grand,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
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
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
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
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn1_omni.save()
        sn1_additional_device = Device(
            node=sn1,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        sn1_additional_device.save()

        links.append(
            Link(
                from_device=sn1_omni,
                to_device=grand_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.MMWAVE,
            )
        )
        links.append(
            Link(
                from_device=sn1_additional_device,
                to_device=grand_additional_device,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )
        links.append(
            Link(
                from_device=grand2_omni,
                to_device=grand_omni,
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
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        grand_omni.save()
        grand_additional_device = Device(
            node=grand,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
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
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
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
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        device_1.save()
        device_2 = Device(
            node=node_2,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        device_2.save()
        device_3 = Device(
            node=node_3,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        device_3.save()

        links.append(
            Link(
                from_device=device_1,
                to_device=device_2,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=device_2,
                to_device=device_3,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=device_3,
                to_device=device_1,
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
                    "from": 555,
                    "to": 99,
                    "status": "active",
                },
                {
                    "from": 99,
                    "to": 731,
                    "status": "active",
                },
                {
                    "from": 731,
                    "to": 555,
                    "status": "active",
                },
            ],
        )

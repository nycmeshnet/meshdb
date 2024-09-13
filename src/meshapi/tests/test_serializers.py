import datetime
import json

from django.contrib.auth.models import User
from django.test import TestCase

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector
from meshapi.tests.sample_data import sample_building, sample_device, sample_install, sample_member, sample_node


class TestViewsGetAdmin(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.client.login(username="admin", password="admin_password")

        sample_install_copy = sample_install.copy()
        self.building_1 = Building(
            id="fc016ea2-847d-42cb-9258-2668c2713229",
            **sample_building,
            panoramas=["http://example.com/test.png"],
            notes="baz bar",
        )
        self.building_1.save()
        sample_install_copy["building"] = self.building_1

        self.building_2 = Building(id="42d63829-ba2b-4cd0-a858-67e7a209b821", **sample_building)
        self.building_2.save()

        self.los = LOS(
            id="1172f792-17b8-4f01-90bb-9b6711a91c41",
            from_building=self.building_1,
            to_building=self.building_2,
            analysis_date=datetime.date(2024, 1, 1),
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            notes="line of sight 1",
        )
        self.los.save()

        self.member = Member(
            id="07927444-3216-4959-858a-2659743ec2a3",
            **sample_member,
            additional_phone_numbers=["+1 555 555 4444"],
            stripe_email_address="foo@bar.com",
            additional_email_addresses=["foobaz@bar.com"],
            notes="foo bar",
        )
        self.member.save()
        sample_install_copy["member"] = self.member

        self.member2 = Member(name="Test Member")
        self.member2.save()

        self.install = Install(
            id="9fdc7357-3174-42d9-b682-2f045d2fea15",
            **sample_install_copy,
            install_number=1,
            referral="foo abc",
            diy=False,
        )
        self.install.save()

        self.node1 = Node(
            id="5d554dca-2c9b-4d8e-a9fc-86bedcea92ea",
            **sample_node,
            install_date=datetime.date(2020, 1, 2),
            abandon_date=datetime.date(2021, 1, 2),
            altitude=44,
            notes="foo asdf",
        )
        self.node1.save()
        self.node1.buildings.add(self.building_1)
        self.node2 = Node(id="5805c953-15e9-4727-8708-b6efada3c491", **sample_node, altitude=88)
        self.node2.save()
        self.node2.buildings.add(self.building_1)

        self.install.node = self.node1
        self.install.save()

        self.building_1.primary_node = self.node1
        self.building_1.save()

        self.device1 = Device(
            id="a5ea27de-a335-40cf-a5be-2c5ab5e2d407",
            **sample_device,
            install_date=datetime.date(2019, 1, 2),
            abandon_date=datetime.date(2023, 1, 2),
            name="nycmesh-device-abc",
            notes="device abc def",
            uisp_id="282d9930-da96-4bc6-b941-054cf2c63573",
        )
        self.device1.node = self.node1
        self.device1.save()

        self.device2 = Device(id="2f32a651-4ea9-4126-96b6-2f323ca28b76", **sample_device)
        self.device2.node = self.node2
        self.device2.save()

        self.sector = Sector(
            id="2d47ee67-7807-4f38-b865-c51cbcc9294c",
            radius=1,
            azimuth=45,
            width=180,
            **sample_device,
            name="nycmesh-sector-1",
            notes="lalalala",
            install_date=datetime.date(2021, 1, 2),
            abandon_date=datetime.date(2022, 1, 2),
            uisp_id="f19be048-5970-4d6d-bbf0-417898adc15f",
        )
        self.sector.node = self.node2
        self.sector.save()

        self.access_point = AccessPoint(
            id="1d4f780c-44f0-4c98-bcee-c37092636407",
            **sample_device,
            latitude=0,
            longitude=0,
            altitude=77,
            name="AP1 east",
            notes="I am an AP",
            install_date=datetime.date(2021, 1, 2),
            abandon_date=datetime.date(2022, 1, 2),
            uisp_id="7b24ddfb-aa1f-4411-8a5d-c59b984c1170",
        )
        self.access_point.node = self.node2
        self.access_point.save()

        self.link = Link(
            id="ae61100b-4a0c-43e7-8957-6502d53d3f1c",
            from_device=self.device1,
            to_device=self.device2,
            status=Link.LinkStatus.ACTIVE,
            notes="abc def ghi",
            description="xyz abc",
            type=Link.LinkType.FIVE_GHZ,
            uisp_id="35eecca6-0186-4a33-9837-451de8b12da0",
            install_date=datetime.date(2016, 1, 2),
            abandon_date=datetime.date(2017, 1, 2),
        )
        self.link.save()

    def _call(self, route, code):
        response = self.client.get(route)
        self.assertEqual(code, response.status_code, f"Could not load {route}")
        return response

    def test_views_get_install(self):
        expected_install = {
            "abandon_date": "9999-01-01",
            "building": "fc016ea2-847d-42cb-9258-2668c2713229",
            "diy": False,
            "id": "9fdc7357-3174-42d9-b682-2f045d2fea15",
            "install_date": "2022-03-01",
            "install_number": 1,
            "member": "07927444-3216-4959-858a-2659743ec2a3",
            "node": {"id": "5d554dca-2c9b-4d8e-a9fc-86bedcea92ea", "network_number": 101},
            "notes": "Referral: Read about it on the internet",
            "referral": "foo abc",
            "request_date": "2022-02-27",
            "roof_access": True,
            "status": "Active",
            "ticket_id": 69,
            "unit": "3",
        }
        response = self._call(f"/api/v1/installs/{self.install.id}/", 200)
        self.assertEqual(json.loads(response.content), expected_install)

        response = self._call(f"/api/v1/installs/{self.install.install_number}/", 200)
        self.assertEqual(json.loads(response.content), expected_install)

    def test_views_get_node(self):
        expected_node = {
            "abandon_date": "2021-01-02",
            "altitude": 44.0,
            "buildings": ["fc016ea2-847d-42cb-9258-2668c2713229"],
            "devices": ["a5ea27de-a335-40cf-a5be-2c5ab5e2d407"],
            "id": "5d554dca-2c9b-4d8e-a9fc-86bedcea92ea",
            "install_date": "2020-01-02",
            "installs": [{"id": "9fdc7357-3174-42d9-b682-2f045d2fea15", "install_number": 1}],
            "latitude": 0.0,
            "longitude": 0.0,
            "name": "Amazing Node",
            "network_number": 101,
            "notes": "foo asdf",
            "status": "Active",
            "type": "Standard",
        }
        response = self._call(f"/api/v1/nodes/{self.node1.id}/", 200)
        self.assertEqual(json.loads(response.content), expected_node)

        response = self._call(f"/api/v1/nodes/{self.node1.network_number}/", 200)
        self.assertEqual(json.loads(response.content), expected_node)

    def test_views_get_member(self):
        response = self._call(f"/api/v1/members/{self.member.id}/", 200)
        self.maxDiff = None
        self.assertEqual(
            json.loads(response.content),
            {
                "additional_email_addresses": ["foobaz@bar.com"],
                "additional_phone_numbers": ["+1 555-555-4444"],
                "all_email_addresses": ["john.smith@example.com", "foo@bar.com", "foobaz@bar.com"],
                "all_phone_numbers": ["+1 555-555-5555", "+1 555-555-4444"],
                "id": "07927444-3216-4959-858a-2659743ec2a3",
                "installs": [{"id": "9fdc7357-3174-42d9-b682-2f045d2fea15", "install_number": 1}],
                "name": "John Smith",
                "notes": "foo bar",
                "phone_number": "+1 555-555-5555",
                "primary_email_address": "john.smith@example.com",
                "slack_handle": "@jsmith",
                "stripe_email_address": "foo@bar.com",
            },
        )

    def test_views_get_building(self):
        response = self._call(f"/api/v1/buildings/{self.building_1.id}/", 200)
        self.assertEqual(
            json.loads(response.content),
            {
                "address_truth_sources": ["NYCPlanningLabs"],
                "altitude": 0.0,
                "bin": 8888,
                "city": "Brooklyn",
                "id": "fc016ea2-847d-42cb-9258-2668c2713229",
                "installs": [{"id": "9fdc7357-3174-42d9-b682-2f045d2fea15", "install_number": 1}],
                "latitude": 0.0,
                "longitude": 0.0,
                "nodes": [
                    {"id": "5d554dca-2c9b-4d8e-a9fc-86bedcea92ea", "network_number": 101},
                    {"id": "5805c953-15e9-4727-8708-b6efada3c491", "network_number": 102},
                ],
                "notes": "baz bar",
                "panoramas": ["http://example.com/test.png"],
                "primary_node": {"id": "5d554dca-2c9b-4d8e-a9fc-86bedcea92ea", "network_number": 101},
                "state": "NY",
                "street_address": "3333 Chom St",
                "zip_code": "11111",
            },
        )

    def test_views_get_device(self):
        response = self._call(f"/api/v1/devices/{self.device1.id}/", 200)
        self.assertEqual(
            json.loads(response.content),
            {
                "abandon_date": "2023-01-02",
                "altitude": 44.0,
                "id": "a5ea27de-a335-40cf-a5be-2c5ab5e2d407",
                "install_date": "2019-01-02",
                "latitude": 0.0,
                "links_from": ["ae61100b-4a0c-43e7-8957-6502d53d3f1c"],
                "links_to": [],
                "longitude": 0.0,
                "name": "nycmesh-device-abc",
                "node": {"id": "5d554dca-2c9b-4d8e-a9fc-86bedcea92ea", "network_number": 101},
                "notes": "device abc def",
                "status": "Active",
                "uisp_id": "282d9930-da96-4bc6-b941-054cf2c63573",
            },
        )

    def test_views_get_link(self):
        response = self._call(f"/api/v1/links/{self.link.id}/", 200)
        self.assertEqual(
            json.loads(response.content),
            {
                "abandon_date": "2017-01-02",
                "description": "xyz abc",
                "from_device": "a5ea27de-a335-40cf-a5be-2c5ab5e2d407",
                "id": "ae61100b-4a0c-43e7-8957-6502d53d3f1c",
                "install_date": "2016-01-02",
                "notes": "abc def ghi",
                "status": "Active",
                "to_device": "2f32a651-4ea9-4126-96b6-2f323ca28b76",
                "type": "5 GHz",
                "uisp_id": "35eecca6-0186-4a33-9837-451de8b12da0",
            },
        )

    def test_views_get_los(self):
        response = self._call(f"/api/v1/loses/{self.los.id}/", 200)
        self.assertEqual(
            json.loads(response.content),
            {
                "analysis_date": "2024-01-01",
                "from_building": "fc016ea2-847d-42cb-9258-2668c2713229",
                "id": "1172f792-17b8-4f01-90bb-9b6711a91c41",
                "notes": "line of sight 1",
                "source": "Human Annotated",
                "to_building": "42d63829-ba2b-4cd0-a858-67e7a209b821",
            },
        )

    def test_views_get_ap(self):
        response = self._call(f"/api/v1/accesspoints/{self.access_point.id}/", 200)
        self.maxDiff = None
        self.assertEqual(
            json.loads(response.content),
            {
                "abandon_date": "2022-01-02",
                "altitude": 77.0,
                "id": "1d4f780c-44f0-4c98-bcee-c37092636407",
                "install_date": "2021-01-02",
                "latitude": 0.0,
                "links_from": [],
                "links_to": [],
                "longitude": 0.0,
                "name": "AP1 east",
                "node": {"id": "5805c953-15e9-4727-8708-b6efada3c491", "network_number": 102},
                "notes": "I am an AP",
                "status": "Active",
                "uisp_id": "7b24ddfb-aa1f-4411-8a5d-c59b984c1170",
            },
        )

    def test_views_get_sector(self):
        response = self._call(f"/api/v1/sectors/{self.sector.id}/", 200)
        self.maxDiff = None
        self.assertEqual(
            json.loads(response.content),
            {
                "abandon_date": "2022-01-02",
                "altitude": 88.0,
                "azimuth": 45,
                "id": "2d47ee67-7807-4f38-b865-c51cbcc9294c",
                "install_date": "2021-01-02",
                "latitude": 0.0,
                "links_from": [],
                "links_to": [],
                "longitude": 0.0,
                "name": "nycmesh-sector-1",
                "node": {"id": "5805c953-15e9-4727-8708-b6efada3c491", "network_number": 102},
                "notes": "lalalala",
                "radius": 1.0,
                "status": "Active",
                "uisp_id": "f19be048-5970-4d6d-bbf0-417898adc15f",
                "width": 180,
            },
        )

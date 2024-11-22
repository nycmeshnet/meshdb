import datetime
import json
import uuid

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector
from .sample_data import sample_building, sample_member


class TestMemberLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        m1 = Member(
            id=uuid.UUID("22f1bfab-fd56-4283-b4cd-8ebd34de4541"),
            **sample_member,
        )
        m1.save()

        m2 = Member(
            id=uuid.UUID("c5a5af9c-35c3-4d04-af87-d917ca4d0d1b"),
            name="Donald Smith",
            primary_email_address="donald.smith@example.com",
            stripe_email_address="donny.stripe@example.com",
            additional_email_addresses=["donny.addl@example.com"],
            phone_number="555-555-6666",
            additional_phone_numbers=["123-555-8888"],
        )
        m2.save()

    def test_member_name_search(self):
        response = self.c.get("/api/v1/members/lookup/?name=Joh")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(response_objs[0]["name"], "John Smith")

    def test_member_email_search(self):
        response = self.c.get("/api/v1/members/lookup/?email_address=donald")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

        response = self.c.get("/api/v1/members/lookup/?email_address=smith")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)
        self.assertEqual(response_objs[0]["name"], "John Smith")
        self.assertEqual(response_objs[1]["name"], "Donald Smith")

    def test_member_alt_email_search(self):
        response = self.c.get("/api/v1/members/lookup/?email_address=stripe")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

        response = self.c.get("/api/v1/members/lookup/?email_address=addl")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

    def test_member_phone_search(self):
        response = self.c.get("/api/v1/members/lookup/?phone_number=6666")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

    def test_member_additional_phone_search(self):
        response = self.c.get("/api/v1/members/lookup/?phone_number=8888")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

    def test_member_combined_search(self):
        response = self.c.get("/api/v1/members/lookup/?phone_number=555&email_address=smith&name=don")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

    def test_empty_search(self):
        response = self.c.get("/api/v1/members/lookup/")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_search(self):
        response = self.c.get("/api/v1/members/lookup/?invalid=abc")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestBuildingLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.n1 = Node(
            network_number=456,
            status=Node.NodeStatus.ACTIVE,
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        self.n1.save()
        self.n2 = Node(
            network_number=789,
            status=Node.NodeStatus.ACTIVE,
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        self.n2.save()

        m1 = Member(**sample_member)
        m1.save()

        b1 = Building(**sample_building, primary_node=self.n2)
        b1.save()

        b2 = Building(
            bin=123,
            street_address="123 Water Road",
            city="New York",
            state="NY",
            zip_code="10025",
            latitude=2,
            longitude=-2,
            altitude=40,
            primary_node=self.n1,
            address_truth_sources=[],
        )
        b2.save()
        b2.nodes.add(self.n2)

        i1 = Install(
            install_number=123,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.datetime.now(),
            building=b1,
            member=m1,
        )
        i1.save()

        i2 = Install(
            install_number=1234,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.datetime.now(),
            building=b2,
            member=m1,
        )
        i2.save()

    def test_building_bin_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?bin=123")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["street_address"], "123 Water Road")

    def test_building_street_address_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?street_address=123 Water Road")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 123)

        response = self.c.get("/api/v1/buildings/lookup/?street_address=123 water road")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 123)

        response = self.c.get("/api/v1/buildings/lookup/?street_address=123 water")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 123)

    def test_city_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?city=Brooklyn")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 8888)

        response = self.c.get("/api/v1/buildings/lookup/?city=new york")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 123)

        response = self.c.get("/api/v1/buildings/lookup/?city=Brook")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_state_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?state=NY")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/buildings/lookup/?state=ny")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/buildings/lookup/?state=PA")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_building_zip_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?zip_code=11111")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 8888)

        response = self.c.get("/api/v1/buildings/lookup/?zip_code=111")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_building_install_number_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?install_number=123")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 8888)

        response = self.c.get("/api/v1/buildings/lookup/?install_number=1234")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 123)

        response = self.c.get("/api/v1/buildings/lookup/?install_number=12")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_building_network_number_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 123)

        response = self.c.get("/api/v1/buildings/lookup/?network_number=789")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/buildings/lookup/?network_number=901")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_building_node_search(self):
        response = self.c.get(f"/api/v1/buildings/lookup/?node={self.n1.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 123)

        response = self.c.get(f"/api/v1/buildings/lookup/?node={self.n2.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/buildings/lookup/?node=fbf35934-55c7-4e06-b1ec-c5b6e06aa643")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_building_primary_network_number_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?primary_network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 123)

        response = self.c.get("/api/v1/buildings/lookup/?primary_network_number=789")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 8888)

        response = self.c.get("/api/v1/buildings/lookup/?primary_network_number=901")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_building_primary_node_search(self):
        response = self.c.get(f"/api/v1/buildings/lookup/?primary_node={self.n1.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 123)

        response = self.c.get(f"/api/v1/buildings/lookup/?primary_node={self.n2.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 8888)

        response = self.c.get("/api/v1/buildings/lookup/?primary_node=fbf35934-55c7-4e06-b1ec-c5b6e06aa643")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_building_combined_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?zip_code=11111&state=NY")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["bin"], 8888)

    def test_empty_search(self):
        response = self.c.get("/api/v1/buildings/lookup/")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_search(self):
        response = self.c.get("/api/v1/buildings/lookup/?invalid=abc")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestInstallLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.n1 = Node(
            network_number=456,
            status=Node.NodeStatus.ACTIVE,
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        self.n1.save()
        self.n2 = Node(
            network_number=789,
            status=Node.NodeStatus.ACTIVE,
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        self.n2.save()

        self.m1 = Member(**sample_member)
        self.m1.save()

        self.b1 = Building(**sample_building, primary_node=self.n2)
        self.b1.save()

        self.b2 = Building(
            bin=123,
            street_address="123 Water Road",
            city="New York",
            state="NY",
            zip_code="10025",
            latitude=2,
            longitude=-2,
            altitude=40,
            primary_node=self.n1,
            address_truth_sources=[],
        )
        self.b2.save()
        self.b2.nodes.add(self.n2)

        i1 = Install(
            install_number=123,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.datetime.now(),
            building=self.b1,
            member=self.m1,
            node=self.n1,
        )
        i1.save()

        i2 = Install(
            install_number=1234,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.datetime.now(),
            building=self.b2,
            member=self.m1,
            node=self.n2,
        )
        i2.save()

        i3 = Install(
            install_number=12345,
            status=Install.InstallStatus.INACTIVE,
            request_date=datetime.datetime.now(),
            building=self.b1,
            member=self.m1,
            node=self.n1,
        )
        i3.save()

    def test_install_network_number_search(self):
        response = self.c.get("/api/v1/installs/lookup/?network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

    def test_install_node_search(self):
        response = self.c.get(f"/api/v1/installs/lookup/?node={self.n1.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

    def test_install_status_search(self):
        response = self.c.get("/api/v1/installs/lookup/?status=Inactive")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["install_number"], 12345)

        response = self.c.get("/api/v1/installs/lookup/?status=Active")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/installs/lookup/?status=Pending")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

        response = self.c.get("/api/v1/installs/lookup/?status=Act")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_install_building_foreign_key_search(self):
        response = self.c.get(f"/api/v1/installs/lookup/?building={self.b1.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get(f"/api/v1/installs/lookup/?building={self.b2.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["install_number"], 1234)

        response = self.c.get("/api/v1/installs/lookup/?building=abcdef")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_install_member_foreign_key_search(self):
        response = self.c.get(f"/api/v1/installs/lookup/?member={self.m1.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 3)

        response = self.c.get("/api/v1/installs/lookup/?member=abcdef")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_install_combined_search(self):
        response = self.c.get(f"/api/v1/installs/lookup/?status=Active&building={self.b2.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["install_number"], 1234)

    def test_empty_search(self):
        response = self.c.get("/api/v1/installs/lookup/")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_search(self):
        response = self.c.get("/api/v1/installs/lookup/?invalid=abc")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestNodeLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        n1 = Node(
            network_number=456,
            status=Node.NodeStatus.ACTIVE,
            name="ABC",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n1.save()
        n2 = Node(
            network_number=789,
            status=Node.NodeStatus.INACTIVE,
            name="DEFG",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n2.save()

        self.m1 = Member(**sample_member)
        self.m1.save()

        self.b1 = Building(**sample_building, primary_node=n2)
        self.b1.save()

        self.b2 = Building(
            bin=123,
            street_address="123 Water Road",
            city="New York",
            state="NY",
            zip_code="10025",
            latitude=2,
            longitude=-2,
            altitude=40,
            primary_node=n1,
            address_truth_sources=[],
        )
        self.b2.save()
        self.b2.nodes.add(n2)

        i1 = Install(
            install_number=123,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.datetime.now(),
            building=self.b1,
            member=self.m1,
            node=n1,
        )
        i1.save()

        i2 = Install(
            install_number=1234,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.datetime.now(),
            building=self.b2,
            member=self.m1,
            node=n2,
        )
        i2.save()

        i3 = Install(
            install_number=12345,
            status=Install.InstallStatus.INACTIVE,
            request_date=datetime.datetime.now(),
            building=self.b1,
            member=self.m1,
        )
        i3.save()

    def test_node_name_search(self):
        response = self.c.get("/api/v1/nodes/lookup/?name=AB")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["network_number"], 456)

        response = self.c.get("/api/v1/nodes/lookup/?name=abc")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["network_number"], 456)

        response = self.c.get("/api/v1/nodes/lookup/?name=xyz")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_node_status_search(self):
        response = self.c.get("/api/v1/nodes/lookup/?status=Inactive")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["network_number"], 789)

        response = self.c.get("/api/v1/nodes/lookup/?status=Active")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["network_number"], 456)

        response = self.c.get("/api/v1/installs/lookup/?status=Pending")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_node_building_foreign_key_search(self):
        response = self.c.get(f"/api/v1/nodes/lookup/?building={self.b1.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["network_number"], 789)

        response = self.c.get(f"/api/v1/nodes/lookup/?building={self.b2.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/nodes/lookup/?building=fbf35934-55c7-4e06-b1ec-c5b6e06aa643")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_install_number_foreign_key_search(self):
        response = self.c.get("/api/v1/nodes/lookup/?install_number=123")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["network_number"], 456)

        response = self.c.get("/api/v1/nodes/lookup/?install_number=1234")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["network_number"], 789)

        response = self.c.get("/api/v1/nodes/lookup/?install_number=12345")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_node_combined_search(self):
        response = self.c.get(f"/api/v1/nodes/lookup/?status=Active&building={self.b2.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["network_number"], 456)

    def test_empty_search(self):
        response = self.c.get("/api/v1/nodes/lookup/")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_search(self):
        response = self.c.get("/api/v1/nodes/lookup/?invalid=abc")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestLinkLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        n1 = Node(
            network_number=456,
            status=Node.NodeStatus.ACTIVE,
            name="ABC",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n1.save()
        n2 = Node(
            network_number=789,
            status=Node.NodeStatus.INACTIVE,
            name="DEFG",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n2.save()
        n3 = Node(
            network_number=123,
            status=Node.NodeStatus.INACTIVE,
            name="DEFG",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n3.save()

        self.d1 = Device(
            node=n1,
            status=Device.DeviceStatus.INACTIVE,
            uisp_id="abc",
            name="nycmesh-456-omni",
        )
        self.d1.save()

        self.d2 = Device(
            node=n2,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="123",
            name="nycmesh-789-omni",
        )
        self.d2.save()

        self.d3 = Device(
            node=n3,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="def",
            name="nycmesh-lbe-789",
        )
        self.d3.save()

        self.l1 = Link(
            from_device=self.d1,
            to_device=self.d2,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIVE_GHZ,
            uisp_id="1231",
        )
        self.l1.save()

        self.l2 = Link(
            from_device=self.d2,
            to_device=self.d3,
            status=Link.LinkStatus.INACTIVE,
        )
        self.l2.save()

    def test_link_nn_search(self):
        response = self.c.get("/api/v1/links/lookup/?network_number=123")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l2.id))

        response = self.c.get("/api/v1/links/lookup/?network_number=789")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/links/lookup/?network_number=321")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_link_node_search(self):
        response = self.c.get(f"/api/v1/links/lookup/?node={self.d3.node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l2.id))

        response = self.c.get(f"/api/v1/links/lookup/?node={self.d2.node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/links/lookup/?node=fbf35934-55c7-4e06-b1ec-c5b6e06aa643")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_link_status_search(self):
        response = self.c.get("/api/v1/links/lookup/?status=Inactive")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l2.id))

        response = self.c.get("/api/v1/links/lookup/?status=Active")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l1.id))

        response = self.c.get("/api/v1/links/lookup/?status=Planned")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_link_type_search(self):
        response = self.c.get("/api/v1/links/lookup/?type=5%20GHz")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l1.id))

        response = self.c.get("/api/v1/links/lookup/?type=VPN")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_link_uisp_id_search(self):
        response = self.c.get("/api/v1/links/lookup/?uisp_id=1231")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l1.id))

        response = self.c.get("/api/v1/links/lookup/?uisp_id=123")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_nn_combined_search(self):
        response = self.c.get("/api/v1/links/lookup/?status=Active&network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l1.id))

    def test_empty_search(self):
        response = self.c.get("/api/v1/links/lookup/")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_search(self):
        response = self.c.get("/api/v1/links/lookup/?invalid=abc")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestLOSLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        n1 = Node(
            network_number=456,
            status=Node.NodeStatus.ACTIVE,
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n1.save()
        n2 = Node(
            network_number=789,
            status=Node.NodeStatus.ACTIVE,
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n2.save()

        m1 = Member(**sample_member)
        m1.save()

        self.b1 = Building(**sample_building, primary_node=n1)
        self.b1.save()

        self.b2 = Building(
            bin=123,
            street_address="123 Water Road",
            city="New York",
            state="NY",
            zip_code="10025",
            latitude=2,
            longitude=-2,
            altitude=40,
            primary_node=n2,
            address_truth_sources=[],
        )
        self.b2.save()
        self.b2.nodes.add(n2)

        self.b3 = Building(
            bin=123,
            street_address="123 Water Road",
            city="New York",
            state="NY",
            zip_code="10025",
            latitude=2,
            longitude=-2,
            altitude=40,
            address_truth_sources=[],
        )
        self.b3.save()

        i1 = Install(
            install_number=123456,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.datetime.now(),
            building=self.b1,
            member=m1,
            node=n1,
        )
        i1.save()

        self.today = datetime.date.today()
        self.l1 = LOS(
            from_building=self.b1,
            to_building=self.b2,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=self.today,
        )
        self.l1.save()

        self.l2 = LOS(
            from_building=self.b2,
            to_building=self.b3,
            source=LOS.LOSSource.EXISTING_LINK,
            analysis_date=self.today,
        )
        self.l2.save()

    def test_los_nn_search(self):
        response = self.c.get("/api/v1/loses/lookup/?network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l1.id))

        response = self.c.get("/api/v1/loses/lookup/?network_number=789")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/loses/lookup/?network_number=321")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_los_node_search(self):
        response = self.c.get(f"/api/v1/loses/lookup/?node={self.b1.primary_node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l1.id))

        response = self.c.get(f"/api/v1/loses/lookup/?node={self.b2.primary_node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)

        response = self.c.get("/api/v1/loses/lookup/?node=fbf35934-55c7-4e06-b1ec-c5b6e06aa643")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_los_install_num_search(self):
        response = self.c.get("/api/v1/loses/lookup/?install_number=123456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l1.id))

        response = self.c.get("/api/v1/loses/lookup/?install_number=321")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_los_building_id_search(self):
        response = self.c.get(f"/api/v1/loses/lookup/?building={self.b3.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)

        response = self.c.get("/api/v1/loses/lookup/?building=fbf35934-55c7-4e06-b1ec-c5b6e06aa643")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_los_source_search(self):
        response = self.c.get("/api/v1/loses/lookup/?source=Existing%20Link")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l2.id))

        response = self.c.get("/api/v1/loses/lookup/?source=Human%20Annotated")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l1.id))

        response = self.c.get("/api/v1/loses/lookup/?source=InvalidABCDEF")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_los_date_search(self):
        response = self.c.get(f"/api/v1/loses/lookup/?analysis_date={self.today.isoformat()}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/loses/lookup/?analysis_date=1968-02-23")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_node_combined_search(self):
        response = self.c.get("/api/v1/loses/lookup/?source=Human%20Annotated&network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.l1.id))

    def test_empty_search(self):
        response = self.c.get("/api/v1/loses/lookup/")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_search(self):
        response = self.c.get("/api/v1/loses/lookup/?invalid=abc")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestDeviceLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        n1 = Node(
            network_number=456,
            status=Node.NodeStatus.ACTIVE,
            name="ABC",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n1.save()
        n2 = Node(
            network_number=789,
            status=Node.NodeStatus.INACTIVE,
            name="DEFG",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n2.save()

        self.d1 = Device(
            node=n1,
            status=Device.DeviceStatus.INACTIVE,
            uisp_id="abc",
        )
        self.d1.save()

        self.d2 = Device(
            node=n2,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="123",
            name="nycmesh-789-omni",
        )
        self.d2.save()

        self.d3 = Device(
            node=n2,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="def",
            name="nycmesh-lbe-789",
        )
        self.d3.save()

    def test_device_nn_search(self):
        response = self.c.get("/api/v1/devices/lookup/?network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.d1.id))

        response = self.c.get("/api/v1/devices/lookup/?network_number=789")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/devices/lookup/?network_number=123")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_device_node_search(self):
        response = self.c.get(f"/api/v1/devices/lookup/?node={self.d1.node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.d1.id))

        response = self.c.get(f"/api/v1/devices/lookup/?node={self.d2.node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/devices/lookup/?node=fbf35934-55c7-4e06-b1ec-c5b6e06aa643")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_device_status_search(self):
        response = self.c.get("/api/v1/devices/lookup/?status=Inactive")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.d1.id))

        response = self.c.get("/api/v1/devices/lookup/?status=Active")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/devices/lookup/?status=Potential")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_device_type_search(self):
        # Device type lookup is no longer supported
        response = self.c.get("/api/v1/devices/lookup/?type=station")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_device_model_name_search(self):
        # Device model lookup is no longer supported
        response = self.c.get("/api/v1/devices/lookup/?model=Litebeam5AC")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_device_combined_search(self):
        response = self.c.get("/api/v1/devices/lookup/?status=Inactive&network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.d1.id))

    def test_empty_search(self):
        response = self.c.get("/api/v1/devices/lookup/")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_search(self):
        response = self.c.get("/api/v1/devices/lookup/?invalid=abc")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestSectorLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        n1 = Node(
            network_number=456,
            status=Node.NodeStatus.ACTIVE,
            name="ABC",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n1.save()
        n2 = Node(
            network_number=789,
            status=Node.NodeStatus.INACTIVE,
            name="DEFG",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n2.save()

        self.s1 = Sector(
            node=n1,
            status=Device.DeviceStatus.INACTIVE,
            uisp_id="abc",
            name="nycmesh-456-east",
            width=120,
            radius=3,
            azimuth=45,
        )
        self.s1.save()

        self.s2 = Sector(
            node=n2,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="123",
            name="nycmesh-789-west",
            width=120,
            radius=3,
            azimuth=45,
        )
        self.s2.save()

        self.s3 = Sector(
            node=n2,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="def",
            name="nycmesh-789-north",
            width=120,
            radius=3,
            azimuth=45,
        )
        self.s3.save()

    def test_sector_nn_search(self):
        response = self.c.get("/api/v1/sectors/lookup/?network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.s1.id))

        response = self.c.get("/api/v1/sectors/lookup/?network_number=789")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/sectors/lookup/?network_number=123")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_sector_node_search(self):
        response = self.c.get(f"/api/v1/sectors/lookup/?node={self.s1.node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.s1.id))

        response = self.c.get(f"/api/v1/sectors/lookup/?node={self.s2.node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/sectors/lookup/?node=fbf35934-55c7-4e06-b1ec-c5b6e06aa643")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_sector_status_search(self):
        response = self.c.get("/api/v1/sectors/lookup/?status=Inactive")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.s1.id))

        response = self.c.get("/api/v1/sectors/lookup/?status=Active")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/sectors/lookup/?status=Potential")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_sector_type_search(self):
        # Type lookup no longer supported
        response = self.c.get("/api/v1/sectors/lookup/?type=ap")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_sector_model_name_search(self):
        # Model lookup no longer supported
        response = self.c.get("/api/v1/sectors/lookup/?model=PrisimStation5AC")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_sector_combined_search(self):
        response = self.c.get("/api/v1/sectors/lookup/?status=Inactive&network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.s1.id))

    def test_empty_search(self):
        response = self.c.get("/api/v1/sectors/lookup/")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_search(self):
        response = self.c.get("/api/v1/sectors/lookup/?invalid=abc")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestAccessPointLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        n1 = Node(
            network_number=456,
            status=Node.NodeStatus.ACTIVE,
            name="ABC",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n1.save()
        n2 = Node(
            network_number=789,
            status=Node.NodeStatus.INACTIVE,
            name="DEFG",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        n2.save()

        self.ap1 = AccessPoint(
            node=n1,
            status=Device.DeviceStatus.INACTIVE,
            uisp_id="abc",
            name="nycmesh-456-east",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        self.ap1.save()

        self.ap2 = AccessPoint(
            node=n2,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="123",
            name="nycmesh-789-west",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        self.ap2.save()

        self.ap3 = AccessPoint(
            id=3,
            node=n2,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="def",
            name="nycmesh-789-north",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        self.ap3.save()

    def test_access_point_nn_search(self):
        response = self.c.get("/api/v1/accesspoints/lookup/?network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.ap1.id))

        response = self.c.get("/api/v1/accesspoints/lookup/?network_number=789")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/accesspoints/lookup/?network_number=123")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_access_point_node_search(self):
        response = self.c.get(f"/api/v1/accesspoints/lookup/?node={self.ap1.node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.ap1.id))

        response = self.c.get(f"/api/v1/accesspoints/lookup/?node={self.ap2.node.id}")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/accesspoints/lookup/?node=fbf35934-55c7-4e06-b1ec-c5b6e06aa643")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_accesspoint_status_search(self):
        response = self.c.get("/api/v1/accesspoints/lookup/?status=Inactive")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.ap1.id))

        response = self.c.get("/api/v1/accesspoints/lookup/?status=Active")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/accesspoints/lookup/?status=Potential")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_accesspoint_combined_search(self):
        response = self.c.get("/api/v1/accesspoints/lookup/?status=Inactive&network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], str(self.ap1.id))

    def test_empty_search(self):
        response = self.c.get("/api/v1/accesspoints/lookup/")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_search(self):
        response = self.c.get("/api/v1/accesspoints/lookup/?invalid=abc")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

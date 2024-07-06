import datetime
import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Building, Device, Install, Link, Member, Node, Sector
from .sample_data import sample_building, sample_member


class TestMemberLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        m1 = Member(**sample_member)
        m1.save()

        m2 = Member(
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

        b1 = Building(**sample_building, primary_node=n2)
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
            primary_node=n1,
            address_truth_sources=[],
        )
        b2.save()
        b2.nodes.add(n2)

        i1 = Install(
            install_number=123,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date.today(),
            building=b1,
            member=m1,
        )
        i1.save()

        i2 = Install(
            install_number=1234,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date.today(),
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

        m1 = Member(id=1, **sample_member)
        m1.save()

        b1 = Building(id=1, **sample_building, primary_node=n2)
        b1.save()

        b2 = Building(
            id=2,
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
        b2.save()
        b2.nodes.add(n2)

        i1 = Install(
            install_number=123,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date.today(),
            building=b1,
            member=m1,
            node=n1,
        )
        i1.save()

        i2 = Install(
            install_number=1234,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date.today(),
            building=b2,
            member=m1,
            node=n2,
        )
        i2.save()

        i3 = Install(
            install_number=12345,
            status=Install.InstallStatus.INACTIVE,
            request_date=datetime.date.today(),
            building=b1,
            member=m1,
            node=n1,
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
        response = self.c.get("/api/v1/installs/lookup/?building=1")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/installs/lookup/?building=2")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["install_number"], 1234)

        response = self.c.get("/api/v1/installs/lookup/?building=3")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_install_member_foreign_key_search(self):
        response = self.c.get("/api/v1/installs/lookup/?member=1")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 3)

        response = self.c.get("/api/v1/installs/lookup/?member=2")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_install_combined_search(self):
        response = self.c.get("/api/v1/installs/lookup/?status=Active&building=2")
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

        m1 = Member(id=1, **sample_member)
        m1.save()

        b1 = Building(id=1, **sample_building, primary_node=n2)
        b1.save()

        b2 = Building(
            id=2,
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
        b2.save()
        b2.nodes.add(n2)

        i1 = Install(
            install_number=123,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date.today(),
            building=b1,
            member=m1,
            node=n1,
        )
        i1.save()

        i2 = Install(
            install_number=1234,
            status=Install.InstallStatus.ACTIVE,
            request_date=datetime.date.today(),
            building=b2,
            member=m1,
            node=n2,
        )
        i2.save()

        i3 = Install(
            install_number=12345,
            status=Install.InstallStatus.INACTIVE,
            request_date=datetime.date.today(),
            building=b1,
            member=m1,
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
        response = self.c.get("/api/v1/nodes/lookup/?building=1")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["network_number"], 789)

        response = self.c.get("/api/v1/nodes/lookup/?building=2")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/nodes/lookup/?building=3")
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
        response = self.c.get("/api/v1/nodes/lookup/?status=Active&building=2")
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

        d1 = Device(
            id=1,
            node=n1,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.INACTIVE,
            uisp_id="abc",
            name="nycmesh-456-omni",
            ssid="nycmesh-456-omni",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        d1.save()

        d2 = Device(
            id=2,
            node=n2,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="123",
            name="nycmesh-789-omni",
            ssid="nycmesh-789-omni",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        d2.save()

        d3 = Device(
            id=3,
            node=n3,
            model="Litebeam5AC",
            type=Device.DeviceType.STATION,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="def",
            name="nycmesh-lbe-789",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        d3.save()

        l1 = Link(
            id=1,
            from_device=d1,
            to_device=d2,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.STANDARD,
            uisp_id="1231",
        )
        l1.save()

        l2 = Link(
            id=2,
            from_device=d2,
            to_device=d3,
            status=Link.LinkStatus.INACTIVE,
        )
        l2.save()

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
        self.assertEqual(response_objs[0]["id"], 2)

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
        self.assertEqual(response_objs[0]["id"], 2)

        response = self.c.get("/api/v1/links/lookup/?status=Active")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], 1)

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
        response = self.c.get("/api/v1/links/lookup/?type=Standard")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], 1)

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
        self.assertEqual(response_objs[0]["id"], 1)

        response = self.c.get("/api/v1/links/lookup/?uisp_id=123")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_node_combined_search(self):
        response = self.c.get("/api/v1/links/lookup/?status=Active&network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], 1)

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

        d1 = Device(
            id=1,
            node=n1,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.INACTIVE,
            uisp_id="abc",
            name="nycmesh-456-omni",
            ssid="nycmesh-456-omni",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        d1.save()

        d2 = Device(
            id=2,
            node=n2,
            model="OmniTik",
            type=Device.DeviceType.ROUTER,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="123",
            name="nycmesh-789-omni",
            ssid="nycmesh-789-omni",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        d2.save()

        d3 = Device(
            id=3,
            node=n2,
            model="Litebeam5AC",
            type=Device.DeviceType.STATION,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="def",
            name="nycmesh-lbe-789",
            latitude=2,
            longitude=-2,
            altitude=40,
        )
        d3.save()

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
        self.assertEqual(response_objs[0]["id"], 1)

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
        self.assertEqual(response_objs[0]["id"], 1)

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
        response = self.c.get("/api/v1/devices/lookup/?type=station")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], 3)

        response = self.c.get("/api/v1/devices/lookup/?type=router")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/devices/lookup/?type=ap")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_device_model_name_search(self):
        response = self.c.get("/api/v1/devices/lookup/?model=Litebeam5AC")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], 3)

        response = self.c.get("/api/v1/devices/lookup/?model=OmniTik")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/devices/lookup/?model=Nanostation")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_node_combined_search(self):
        response = self.c.get("/api/v1/devices/lookup/?model=OmniTik&network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], 1)

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

        s1 = Sector(
            id=1,
            node=n1,
            model="LAP-120",
            type=Device.DeviceType.AP,
            status=Device.DeviceStatus.INACTIVE,
            uisp_id="abc",
            name="nycmesh-456-east",
            ssid="nycmesh-456-east",
            latitude=2,
            longitude=-2,
            altitude=40,
            width=120,
            radius=3,
            azimuth=45,
        )
        s1.save()

        s2 = Sector(
            id=2,
            node=n2,
            model="LAP-120",
            type=Device.DeviceType.AP,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="123",
            name="nycmesh-789-west",
            ssid="nycmesh-789-west",
            latitude=2,
            longitude=-2,
            altitude=40,
            width=120,
            radius=3,
            azimuth=45,
        )
        s2.save()

        s3 = Sector(
            id=3,
            node=n2,
            model="PrisimStation5AC",
            type=Device.DeviceType.AP,
            status=Device.DeviceStatus.ACTIVE,
            uisp_id="def",
            name="nycmesh-789-north",
            latitude=2,
            longitude=-2,
            altitude=40,
            width=120,
            radius=3,
            azimuth=45,
        )
        s3.save()

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
        self.assertEqual(response_objs[0]["id"], 1)

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
        self.assertEqual(response_objs[0]["id"], 1)

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
        response = self.c.get("/api/v1/sectors/lookup/?type=ap")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 3)

        response = self.c.get("/api/v1/sectors/lookup/?type=router")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_sector_model_name_search(self):
        response = self.c.get("/api/v1/sectors/lookup/?model=PrisimStation5AC")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], 3)

        response = self.c.get("/api/v1/sectors/lookup/?model=LAP-120")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)

        response = self.c.get("/api/v1/sectors/lookup/?model=Nanostation")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 0)

    def test_node_combined_search(self):
        response = self.c.get("/api/v1/sectors/lookup/?model=LAP-120&network_number=456")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["id"], 1)

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

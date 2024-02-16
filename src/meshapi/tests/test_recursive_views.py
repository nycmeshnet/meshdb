import json

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase

from meshapi.models import Building, Install, Member
from meshapi.tests.sample_data import sample_building, sample_install, sample_member


def setup_objects():
    member_obj = Member(id=1, **sample_member)
    member_obj.save()
    building = sample_building.copy()
    building["primary_nn"] = None
    building_obj = Building(id=1, **building)
    building_obj.save()
    inst = sample_install.copy()

    if inst["abandon_date"] == "":
        inst["abandon_date"] = None

    inst["building"] = building_obj
    inst["member"] = member_obj
    inst["install_number"] = 2000
    install_obj = Install(**inst)
    install_obj.save()


class TestViewsGetLimitedPermissions(TestCase):
    c = Client()

    def setUp(self):
        # Create sample data
        setup_objects()

        self.no_member_perm_user = User.objects.create_user(
            username="limited_install", password="password", email="installer@example.com"
        )
        self.no_member_perm_user.user_permissions.add(Permission.objects.get(codename="view_install"))
        self.no_member_perm_user.user_permissions.add(Permission.objects.get(codename="view_building"))

        self.no_install_perm_user = User.objects.create_user(
            username="limited_member", password="password", email="installer@example.com"
        )
        self.no_install_perm_user.user_permissions.add(Permission.objects.get(codename="view_member"))
        self.no_install_perm_user.user_permissions.add(Permission.objects.get(codename="view_building"))

    def test_views_get_install(self):
        self.c.login(username="limited_install", password="password")

        response = self.c.get("/api/v1/installs/2000/").json()
        self.assertEqual(response["unit"], "3")
        self.assertEqual(
            response["member"],
            {
                "id": 1,
            },
        )
        self.assertEqual(
            response["building"],
            {
                "id": 1,
                "bin": 8888,
                "building_status": "Active",
                "street_address": "3333 Chom St",
                "city": "Brooklyn",
                "state": "NY",
                "zip_code": "11111",
                "invalid": False,
                "address_truth_sources": "['NYCPlanningLabs']",
                "latitude": 0.0,
                "longitude": 0.0,
                "altitude": 0.0,
                "primary_nn": None,
                "node_name": None,
                "notes": None,
            },
        )

        self.c.login(username="limited_member", password="password")

        response = self.c.get("/api/v1/installs/1/")
        self.assertEqual(response.status_code, 403)

    def test_views_get_member(self):
        self.c.login(username="limited_install", password="password")

        response = self.c.get("/api/v1/members/1/")
        self.assertEqual(response.status_code, 403)

        self.c.login(username="limited_member", password="password")

        response = self.c.get("/api/v1/members/1/").json()
        self.assertEqual(response["primary_email_address"], "john.smith@example.com")
        self.assertEqual(
            response["installs"],
            [
                {
                    "install_number": 2000,
                }
            ],
        )

    def test_views_get_building(self):
        self.c.login(username="limited_install", password="password")

        response = self.c.get("/api/v1/buildings/1/").json()
        self.assertEqual(response["bin"], 8888)
        self.assertEqual(
            response["installs"],
            [
                {
                    "install_number": 2000,
                    "member": {
                        "id": 1,
                    },
                    "network_number": 2000,
                    "install_status": "Active",
                    "ticket_id": 69,
                    "request_date": "2022-02-27",
                    "install_date": "2022-03-01",
                    "abandon_date": "9999-01-01",
                    "unit": "3",
                    "roof_access": True,
                    "referral": None,
                    "notes": "Referral: Read about it on the internet",
                    "diy": None,
                }
            ],
        )

        self.c.login(username="limited_member", password="password")

        response = self.c.get("/api/v1/buildings/1/").json()
        self.assertEqual(response["bin"], 8888)
        self.assertEqual(
            response["installs"],
            [
                {
                    "install_number": 2000,
                }
            ],
        )


class TestViewsGetAdmin(TestCase):
    c = Client()

    def setUp(self):
        # Create sample data
        setup_objects()

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )

    def test_views_get_install(self):
        self.c.login(username="admin", password="admin_password")

        response = self.c.get("/api/v1/installs/2000/").json()
        self.assertEqual(response["unit"], "3")
        self.assertEqual(
            response["member"],
            {
                "id": 1,
                "name": "John Smith",
                "primary_email_address": "john.smith@example.com",
                "stripe_email_address": None,
                "additional_email_addresses": [],
                "phone_number": "555-555-5555",
                "slack_handle": "@jsmith",
                "invalid": False,
                "contact_notes": None,
            },
        )
        self.assertEqual(
            response["building"],
            {
                "id": 1,
                "bin": 8888,
                "building_status": "Active",
                "street_address": "3333 Chom St",
                "city": "Brooklyn",
                "state": "NY",
                "zip_code": "11111",
                "invalid": False,
                "address_truth_sources": "['NYCPlanningLabs']",
                "latitude": 0.0,
                "longitude": 0.0,
                "altitude": 0.0,
                "primary_nn": None,
                "node_name": None,
                "notes": None,
            },
        )

    def test_views_get_member(self):
        self.c.login(username="admin", password="admin_password")

        response = self.c.get("/api/v1/members/1/").json()
        self.assertEqual(response["primary_email_address"], "john.smith@example.com")
        self.assertEqual(
            response["installs"],
            [
                {
                    "install_number": 2000,
                    "building": {
                        "id": 1,
                        "bin": 8888,
                        "building_status": "Active",
                        "street_address": "3333 Chom St",
                        "city": "Brooklyn",
                        "state": "NY",
                        "zip_code": "11111",
                        "invalid": False,
                        "address_truth_sources": "['NYCPlanningLabs']",
                        "latitude": 0.0,
                        "longitude": 0.0,
                        "altitude": 0.0,
                        "primary_nn": None,
                        "node_name": None,
                        "notes": None,
                    },
                    "network_number": 2000,
                    "install_status": "Active",
                    "ticket_id": 69,
                    "request_date": "2022-02-27",
                    "install_date": "2022-03-01",
                    "abandon_date": "9999-01-01",
                    "unit": "3",
                    "roof_access": True,
                    "referral": None,
                    "notes": "Referral: Read about it on the internet",
                    "diy": None,
                }
            ],
        )

    def test_views_get_building(self):
        self.c.login(username="admin", password="admin_password")

        response = self.c.get("/api/v1/buildings/1/").json()
        self.assertEqual(response["bin"], 8888)
        self.assertEqual(
            response["installs"],
            [
                {
                    "install_number": 2000,
                    "member": {
                        "id": 1,
                        "name": "John Smith",
                        "primary_email_address": "john.smith@example.com",
                        "stripe_email_address": None,
                        "additional_email_addresses": [],
                        "phone_number": "555-555-5555",
                        "slack_handle": "@jsmith",
                        "invalid": False,
                        "contact_notes": None,
                    },
                    "network_number": 2000,
                    "install_status": "Active",
                    "ticket_id": 69,
                    "request_date": "2022-02-27",
                    "install_date": "2022-03-01",
                    "abandon_date": "9999-01-01",
                    "unit": "3",
                    "roof_access": True,
                    "referral": None,
                    "notes": "Referral: Read about it on the internet",
                    "diy": None,
                }
            ],
        )


class TestViewsPutAdmin(TestCase):
    c = Client()

    def setUp(self):
        # Create sample data
        setup_objects()

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )

    def test_views_put_new_install_with_pk(self):
        self.c.login(username="admin", password="admin_password")

        inst = sample_install.copy()

        if inst["abandon_date"] == "":
            inst["abandon_date"] = None

        inst["building"] = 1
        inst["member"] = 1
        inst["install_number"] = 2001

        response = self.c.post("/api/v1/installs/", inst)
        self.assertEqual(response.status_code, 201)

        install = Install.objects.get(install_number=response.json()["install_number"])
        self.assertEqual(install.member.id, 1)
        self.assertEqual(install.member.primary_email_address, "john.smith@example.com")
        self.assertEqual(install.building.id, 1)
        self.assertEqual(install.building.bin, 8888)

    def test_views_post_new_install_with_nested_data_not_allowed(self):
        self.c.login(username="admin", password="admin_password")

        inst = sample_install.copy()

        if inst["abandon_date"] == "":
            inst["abandon_date"] = None

        inst["building"] = 1
        inst["member"] = sample_member
        inst["install_number"] = 2001

        response = self.c.post("/api/v1/installs/", inst)
        self.assertEqual(response.status_code, 400)

    def test_views_put_install_with_nested_data_not_allowed(self):
        self.c.login(username="admin", password="admin_password")

        inst = sample_install.copy()

        if inst["abandon_date"] == "":
            inst["abandon_date"] = None

        inst["building"] = 1
        inst["member"] = sample_member
        inst["install_number"] = 2000

        response = self.c.put("/api/v1/installs/2000/", json.dumps(inst), content_type="application/json")
        self.assertEqual(response.status_code, 400)

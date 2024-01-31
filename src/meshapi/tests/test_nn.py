import json

from django.conf import os
from django.contrib.auth.models import User
from django.test import Client, TestCase

from meshapi.models import Building, Install, Member

from .group_helpers import create_groups
from .sample_data import sample_building, sample_install, sample_member


# Test basic NN form stuff (input validation, etc)
class TestNN(TestCase):
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # Create sample data
        member_obj = Member(**sample_member)
        member_obj.save()
        building = sample_building.copy()
        building["primary_nn"] = None
        building_obj = Building(**building)
        building_obj.save()
        inst = sample_install.copy()

        if inst["abandon_date"] == "":
            inst["abandon_date"] = None

        inst["building"] = building_obj
        inst["member"] = member_obj
        inst["network_number"] = None
        install_obj = Install(**inst)
        install_obj.save()

        self.install_number = install_obj.install_number

    def test_nn_valid_install_number(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": os.environ.get("NN_ASSIGN_PSK")},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = 101
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        # Now test to make sure that we get 200 for dupes
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": os.environ.get("NN_ASSIGN_PSK")},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number DUPLICATE. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = 101
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

    def test_nn_invalid_password(self):
        unauth_client = Client()
        response = unauth_client.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": "chom"},
            content_type="application/json",
        )

        code = 403
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

    def test_nn_no_password_admin(self):
        installer_client = Client()
        installer = User.objects.create_superuser(
            username="installer", password="installer_password", email="admin@example.com"
        )
        _, installer_group, _ = create_groups()
        installer.groups.add(installer_group)
        installer_client.login(username="installer", password="installer_password")

        response = installer_client.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

    def test_nn_no_password_installer(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

    def test_nn_invalid_building_id(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": 69420, "password": os.environ.get("NN_ASSIGN_PSK")},
            content_type="application/json",
        )

        code = 404
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_invalid_building_id. Should be {code}, but got {response.status_code}",
        )

    def test_nn_bad_request(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": "chom", "password": os.environ.get("NN_ASSIGN_PSK")},
            content_type="application/json",
        )

        code = 404
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_invalid_building_id. Should be {code}, but got {response.status_code}",
        )

        response = self.admin_c.post("/api/v1/nn-assign/", "Tell me your secrets >:)", content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_invalid_building_id. Should be {code}, but got {response.status_code}",
        )


# Test that the NN function can find gaps
class TestFindGaps(TestCase):
    c = Client()
    admin_c = Client()

    def add_data(self, b, m, i, index=101, nn=False):
        b["zip_code"] += index
        b["address_truth_sources"] = ["NYCPlanningLabs"]

        if nn:
            b["primary_nn"] = index
            i["network_number"] = index
        else:
            b["primary_nn"] = None
            i["network_number"] = None

        if i["abandon_date"] == "":
            i["abandon_date"] = None

        if "install_number" in i:
            i["install_number"] = None

        building_obj = Building(**b)
        building_obj.save()
        i["building"] = building_obj

        m["email_address"] = f"john{index}@gmail.com"
        member_obj = Member(**m)
        member_obj.save()
        i["member"] = member_obj
        i["ticket_id"] = index
        install_obj = Install(**i)
        install_obj.save()
        i["install_number"] = install_obj.install_number

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # Create a whole bunch of sample data
        build = sample_building.copy()
        inst = sample_install.copy()
        memb = sample_member.copy()
        build["street_address"] = "123 Fake St"
        for i in range(101, 111):
            self.add_data(build, memb, inst, index=i, nn=True)

        # Skip a few numbers (111, 112)
        for i in range(113, 130):
            self.add_data(build, memb, inst, index=i, nn=True)

        # Then create another couple installs
        # These will get numbers assigned next
        b2 = sample_building.copy()
        m2 = sample_member.copy()
        self.inst2 = sample_install.copy()
        self.add_data(b2, m2, self.inst2, index=5002, nn=False)

        b3 = sample_building.copy()
        m3 = sample_member.copy()
        self.inst3 = sample_install.copy()
        self.add_data(b3, m3, self.inst3, index=5003, nn=False)

        b4 = sample_building.copy()
        m4 = sample_member.copy()
        self.inst4 = sample_install.copy()
        self.add_data(b4, m4, self.inst4, index=5004, nn=False)

    def test_nn_search_for_new_number(self):
        # Try to give NNs to all the installs. Should end up with two right
        # next to each other and then one at the end.

        for inst, nn in [(self.inst2, 111), (self.inst3, 112), (self.inst4, 130)]:
            response = self.admin_c.post(
                "/api/v1/nn-assign/",
                {"install_number": inst["install_number"], "password": os.environ.get("NN_ASSIGN_PSK")},
                content_type="application/json",
            )
            response.content.decode("utf-8")

            code = 201
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for test_nn_valid_building_id. Should be {code}, but got {response.status_code}",
            )

            resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
            expected_nn = nn

            self.assertEqual(
                resp_nn,
                expected_nn,
                f"Got wrong nn for install {inst['install_number']}. Got {resp_nn} but expected {expected_nn}",
            )

        # Sanity check that the other buildings actually exist
        self.assertIsNotNone(Install.objects.filter(network_number=129)[0].install_number)
        self.assertIsNotNone(Building.objects.filter(primary_nn=129)[0].id)

        self.assertIsNotNone(Install.objects.filter(network_number=130)[0].install_number)
        self.assertIsNotNone(Building.objects.filter(primary_nn=130)[0].id)

import json
from django.contrib.auth.models import User
from django.test import TestCase, Client
from meshapi.models import Building, Install, Member

from .sample_data import sample_member, sample_building, sample_install


# Test basic NN form stuff (input validation, etc)
class TestNN(TestCase):
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # Create sample data
        self.admin_c.post("/api/v1/members/", sample_member)
        building = sample_building.copy()
        building["primary_nn"] = "" 
        self.admin_c.post("/api/v1/buildings/", building)
        inst = sample_install.copy()
        inst["building_id"] = Building.objects.all()[0].id
        inst["member_id"] = Member.objects.all()[0].id
        inst["network_number"] = ""
        self.admin_c.post("/api/v1/installs/", inst)

        self.install_number = Install.objects.all()[0].install_number

    def test_nn_valid_install_number(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/", {"install_number": self.install_number}, content_type="application/json"
        )

        code = 200
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

    def test_nn_invalid_building_id(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/", {"install_number": 69420}, content_type="application/json"
        )

        code = 404
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_invalid_building_id. Should be {code}, but got {response.status_code}",
        )

    def test_nn_bad_request(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/", {"install_number": "chom"}, content_type="application/json"
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
#class TestNNSearchForNewNumber(TestCase):
#    c = Client()
#    admin_c = Client()
#
#    def add_data(self, b, m, i, index=101, nn=False):
#        b["zip_code"] += index
#
#        if nn:
#            b["primary_nn"] = index
#            i["network_number"] = index
#        else:
#            b["primary_nn"] = ""
#            i["network_number"] = ""
#
#        self.admin_c.post("/api/v1/buildings/", b)
#
#        m["email_address"] = f"john{index}@gmail.com"
#        self.admin_c.post("/api/v1/members/", m)
#
#        i["building_id"] = Building.objects.filter(zip_code=b["zip_code"])[0].id
#        i["member_id"] = Member.objects.filter(email_address=m["email_address"])[0].id
#        i["ticket_id"] = index
#        self.admin_c.post("/api/v1/installs/", i)
#        i["install_number"] = Install.objects.filter(ticket_id=i["ticket_id"])[0].install_number
#
#    def setUp(self):
#        self.admin_user = User.objects.create_superuser(
#            username="admin", password="admin_password", email="admin@example.com"
#        )
#        self.admin_c.login(username="admin", password="admin_password")
#
#        # Create a whole bunch of sample data
#        build = sample_building.copy()
#        inst = sample_install.copy()
#        memb = sample_member.copy()
#        build["street_address"] = "123 Fake St"
#        for i in range(101, 111):
#            self.add_data(build, memb, inst, index=i, nn=True)
#
#        # Skip a few numbers (111, 112)
#        for i in range(113, 130):
#            self.add_data(build, memb, inst, index=i, nn=True)
#
#        # Then create another couple installs
#        # These will get numbers assigned next
#        b2 = sample_building.copy()
#        m2 = sample_member.copy()
#        self.inst2 = sample_install.copy()
#        self.add_data(b2, m2, self.inst2, index=5002, nn=False)
#
#
#        b3 = sample_building.copy()
#        m3 = sample_member.copy()
#        self.inst3 = sample_install.copy()
#        b3["street_address"] = "123 Fake St"
#        self.add_data(b3, m3, self.inst3, index=5003, nn=False)
#
#        b4 = sample_building.copy()
#        m4 = sample_member.copy()
#        self.inst4 = sample_install.copy()
#        b4["street_address"] = "123 Fake St"
#        self.add_data(b4, m4, self.inst4, index=5003, nn=False)
#
#
#    def test_nn_search_for_new_number(self):
#        # Try to give NNs to all the installs. Should end up with two right
#        # next to each other and then one at the end.
#
#        for inst, nn in [(self.inst2, 111), (self.inst3, 112), (self.inst4, 130)]:
#            response = self.admin_c.post(
#                "/api/v1/nn-assign/", {"install_number": inst["install_number"]}, content_type="application/json"
#            )
#            response.content.decode("utf-8")
#
#            code = 200
#            self.assertEqual(
#                code,
#                response.status_code,
#                f"status code incorrect for test_nn_valid_building_id. Should be {code}, but got {response.status_code}",
#            )
#
#            resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
#            expected_nn = nn
#            self.assertEqual(
#                resp_nn,
#                expected_nn,
#                f"Got wrong nn for install {inst['install_number']}. Got {resp_nn} but expected {expected_nn}",
#            )
#
#        # Sanity check that the other buildings actually exist
#        self.assertIsNotNone(Install.objects.filter(network_number=129)[0].id)
#        self.assertIsNotNone(Building.objects.filter(primary_nn=129)[0].id)

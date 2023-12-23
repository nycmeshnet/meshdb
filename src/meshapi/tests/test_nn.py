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
        self.admin_c.post("/api/v1/buildings/", sample_building)
        self.admin_c.post("/api/v1/installs/", sample_install)

        self.install_number = Install.objects.all()[0].id

    def test_nn_valid_install_number(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/", {"install_number": self.install_number}, content_type="application/json"
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_building_id. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["node_number"]
        expected_bid = 101
        self.assertEqual(
            expected_bid,
            resp_nn,
            f"status code incorrect for test_nn_valid_building_id. Should be {code}, but got {response.status_code}",
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
class TestNNSearchForNewNetworkNumber(TestCase):
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")




# Test that the NN function can find gaps
class TestNNSearchForNewNumber(TestCase):
    c = Client()
    admin_c = Client()

    def add_data(self, b, m, i, index=101, nn=False):
        b["zip_code"] += index
        if nn:
            b["primary_nn"] = 1000 + index
        self.admin_c.post("/api/v1/buildings/", b)

        m["email_address"] = f"john{index}@gmail.com"
        self.admin_c.post("/api/v1/members/", m)

        if nn:
            i["network_number"] = 1000 + index
        i["building_id"] = Building.objects.filter(zip_code=b["zip_code"])[0].id
        i["member_id"] = Member.objects.filter(email_address=m["email_address"])[0].id
        self.admin_c.post("/api/v1/installs/", i)

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # Create a whole bunch of sample data
        b = sample_building.copy()
        inst = sample_install.copy()
        member = sample_member.copy()
        b["street_address"] = "123 Fake St"
        for i in range(101, 111):

            self.add_data(b, m, i, index=101, nn=False):

            b["zip_code"] += 1
            b["primary_nn"] = i
            self.admin_c.post("/api/v1/buildings/", b)

            member["email_address"] = f"john{i}@gmail.com"
            self.admin_c.post("/api/v1/members/", member)

            inst["network_number"] = i
            inst["building_id"] = Building.objects.filter(zip_code=b["zip_code"])[0].id
            inst["member_id"] = Member.objects.filter(email_address=member["email_address"])[0].id
            self.admin_c.post("/api/v1/installs/", inst)

        # Skip a few numbers (111, 112)
        for i in range(113, 130):
            b["zip_code"] += 1
            b["primary_nn"] = i
            self.admin_c.post("/api/v1/buildings/", b)

            member["email_address"] = f"john{i}@gmail.com"
            self.admin_c.post("/api/v1/members/", member)

            inst["network_number"] = i
            inst["building_id"] = Building.objects.filter(zip_code=b["zip_code"])[0].id
            inst["member_id"] = Member.objects.filter(email_address=member["email_address"])[0].id
            self.admin_c.post("/api/v1/installs/", inst)

        # Then create another couple installs
        # These will get numbers assigned next
        b2 = sample_building.copy()
        m2 = sample_member.copy()
        self.inst2 = sample_install.copy()
        b2["street_address"] = "123 Fake St"
        b2["zip_code"] = 12002
        self.admin_c.post("/api/v1/buildings/", b2)

        m2["email_address"] = f"john5002@gmail.com"
        self.admin_c.post("/api/v1/members/", m2)

        self.inst2["building_id"] = Building.objects.filter(zip_code=b2["zip_code"])[0].id
        inst["member_id"] = Member.objects.filter(email_address=m2["email_address"])[0].id
        self.inst2["ticket_id"] = 5002
        resp = self.admin_c.post("/api/v1/installs/", self.inst2)
        print(resp.content.decode("utf-8"))
        self.inst2["install_number"] = Install.objects.filter(ticket_id=self.inst2["ticket_id"])[0].install_number

        b3 = sample_building.copy()
        self.inst3 = sample_install.copy()
        b3["street_address"] = "123 Fake St"
        b3["zip_code"] = 12003
        self.admin_c.post("/api/v1/buildings/", b3)
        self.inst3["building_id"] = Building.objects.filter(zip_code=b3["zip_code"])[0].id
        self.inst3["ticket_id"] = 5003
        self.admin_c.post("/api/v1/installs/", self.inst3)
        self.inst3["install_number"] = Install.objects.filter(ticket_id=self.inst3["ticket_id"])[0].install_number

        b4 = sample_building.copy()
        self.inst4 = sample_install.copy()
        b4["street_address"] = "123 Fake St"
        b4["zip_code"] += 12002
        self.admin_c.post("/api/v1/buildings/", b4)
        self.inst4["building_id"] = Building.objects.filter(zip_code=b4["zip_code"])[0].id
        self.inst4["ticket_id"] = 5004
        self.admin_c.post("/api/v1/installs/", self.inst4)
        self.inst4["install_number"] = Install.objects.filter(ticket_id=self.inst4["ticket_id"])[0].install_number


    def test_nn_search_for_new_number(self):
        # Try to give NNs to all the installs. Should end up with two right
        # next to each other and then one at the end.

        for inst, nn in [(self.inst2, 111), (self.inst3, 112), (self.inst4, 130)]:
            response = self.admin_c.post(
                "/api/v1/nn-assign/", {"install_number": inst["install_number"]}, content_type="application/json"
            )

            code = 200
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for test_nn_valid_building_id. Should be {code}, but got {response.status_code}",
            )

            resp_nn = json.loads(response.content.decode("utf-8"))["node_number"]
            expected_nn = nn
            self.assertEqual(
                expected_nn,
                resp_nn,
                f"status code incorrect for test_nn_valid_building_id. Should be {code}, but got {response.status_code}",
            )

        # Sanity check that the other buildings actually exist
        self.assertIsNotNone(Install.objects.filter(network_number=129)[0].id)
        self.assertIsNotNone(Building.objects.filter(primary_nn=129)[0].id)

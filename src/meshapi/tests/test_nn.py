import json
from django.contrib.auth.models import User
from django.test import TestCase, Client
from meshapi.models import Building

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

        self.building_id = Building.objects.filter(street_address=sample_building["street_address"])[0].id

    def test_nn_valid_building_id(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/", {"meshapi_building_id": self.building_id}, content_type="application/json"
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
            "/api/v1/nn-assign/", {"meshapi_building_id": 69420}, content_type="application/json"
        )

        code = 404
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_invalid_building_id. Should be {code}, but got {response.status_code}",
        )

    def test_nn_bad_request(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/", {"meshapi_building_id": "chom"}, content_type="application/json"
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
class TestNNSearchForNewNumber(TestCase):
    c = Client()
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # Create a whole bunch of sample data
        b = sample_building.copy()
        b["street_address"] = "123 Fake St"
        for i in range(101, 111):
            b["zip_code"] += 1
            b["network_number"] = i
            self.admin_c.post("/api/v1/buildings/", b)

        # Skip a few numbers
        for i in range(113, 130):
            b["zip_code"] += 1
            b["network_number"] = i
            self.admin_c.post("/api/v1/buildings/", b)

        # Then create another couple buildings
        b2 = sample_building.copy()
        b2["zip_code"] = 11002
        self.admin_c.post("/api/v1/buildings/", b2)
        self.b2_bid = Building.objects.filter(zip_code=b2["zip_code"])[0].id

        b3 = sample_building.copy()
        b3["zip_code"] = 11003
        self.admin_c.post("/api/v1/buildings/", b3)
        self.b3_bid = Building.objects.filter(zip_code=b3["zip_code"])[0].id

        b4 = sample_building.copy()
        b4["zip_code"] = 11004
        self.admin_c.post("/api/v1/buildings/", b4)
        self.b4_bid = Building.objects.filter(zip_code=b4["zip_code"])[0].id

    def test_nn_search_for_new_number(self):
        # Try to give NNs to all the buildings. Should end up with two right next to each other
        # and then one at the end.

        for b_id, nn in [(self.b2_bid, 111), (self.b3_bid, 112), (self.b4_bid, 130)]:
            response = self.admin_c.post(
                "/api/v1/nn-assign/", {"meshapi_building_id": b_id}, content_type="application/json"
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
        self.assertIsNotNone(Building.objects.filter(network_number=129)[0].id)

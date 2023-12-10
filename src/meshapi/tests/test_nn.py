import json
from django.contrib.auth.models import User
from django.test import TestCase, Client
from meshapi.models import Building
from meshapi.views import NewNodeRequest

from .sample_data import *


class TestNN(TestCase):
    c = Client()
    admin_c = Client()
    building_id = 1

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # Create sample data
        m_response = self.admin_c.post("/api/v1/members/", sample_member)
        b_response = self.admin_c.post("/api/v1/buildings/", sample_building)
        i_response = self.admin_c.post("/api/v1/installs/", sample_install)
        r_response = self.admin_c.post("/api/v1/requests/", sample_request)

    def test_nn_valid_building_id(self):
        response = self.admin_c.post(
            "/api/v1/new-node/", {"meshapi_building_id": self.building_id}, content_type="application/json"
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_building_id. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode('utf-8'))["node_number"]
        expected_bid = 101
        self.assertEqual(
            expected_bid,
            resp_nn,
            f"status code incorrect for test_nn_valid_building_id. Should be {code}, but got {response.status_code}",
        )

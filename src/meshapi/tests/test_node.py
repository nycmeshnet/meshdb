import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Node
from .sample_data import sample_node


class TestNode(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.node1 = Node(**sample_node, network_number=101)
        self.node1.save()

        self.node128 = Node(**sample_node, network_number=128)
        self.node128.save()

    def test_new_node(self):
        response = self.c.post(
            "/api/v1/nodes/",
            {
                "network_number": 123,
                "latitude": 0,
                "longitude": 0,
                "status": "Active",
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_new_node_with_blank_nn_respects_taken_nns(self):
        node2 = Node(network_number=103, **sample_node)
        node2.save()

        response = self.c.post(
            "/api/v1/nodes/",
            {
                "latitude": 0,
                "longitude": 0,
                "status": "Active",
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 102)

        response = self.c.post(
            "/api/v1/nodes/",
            {
                "latitude": 0,
                "longitude": 0,
                "status": "Active",
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 104)

    def test_broken_node(self):
        response = self.c.post(
            "/api/v1/nodes/",
            {
                "network_number": 123,
                "latitude": 0,
                "longitude": 0,
                # Missing status
            },
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_steal_taken_nn(self):
        response = self.c.post(
            "/api/v1/nodes/",
            {
                "network_number": 101,
                "latitude": 0,
                "longitude": 0,
                "status": "Active",
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 102)
        self.assertEqual(len(Node.objects.all()), 3)

    def test_get_node(self):
        response = self.c.get(f"/api/v1/nodes/{self.node1.network_number}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["name"], "Amazing Node")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], None)

    def test_modify_node(self):
        response = self.c.patch(
            f"/api/v1/nodes/{self.node1.network_number}/",
            {"notes": "New notes! Wheee"},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["name"], "Amazing Node")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], "New notes! Wheee")

    def test_cant_modify_existing_node_nn(self):
        response = self.c.patch(
            f"/api/v1/nodes/{self.node128.network_number}/",
            {"network_number": 123},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 128)
        self.node128.refresh_from_db()
        self.assertEqual(self.node128.network_number, 128)

    def test_cant_remove_existing_node_nn(self):
        response = self.c.put(
            f"/api/v1/nodes/{self.node128.network_number}/",
            sample_node,
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 128)
        self.node128.refresh_from_db()
        self.assertEqual(self.node128.network_number, 128)

    def test_delete_node(self):
        network_num = self.node1.network_number
        response = self.c.delete(f"/api/v1/nodes/{network_num}/")

        code = 204
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        self.assertEqual(0, len(Node.objects.filter(network_number=network_num)))

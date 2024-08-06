import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import AccessPoint, Device, Node
from .sample_data import sample_node


class TestAccessPoint(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.node = Node(
            network_number=7,
            name="Test Node",
            status=Node.NodeStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        self.node.save()

    def test_new_accesspoint(self):
        response = self.c.post(
            "/api/v1/accesspoints/",
            {
                "network_number": self.node.network_number,
                "status": Device.DeviceStatus.ACTIVE,
                "latitude": 0,
                "longitude": 0,
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_broken_accesspoint(self):
        response = self.c.post(
            "/api/v1/accesspoints/",
            {
                "name": "Vernon",
                "network_number": self.node.network_number,
                "latitude": 0,
                "longitude": 0,
            },
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_get_accesspoint(self):
        node = Node(**sample_node)
        node.save()
        accesspoint = AccessPoint(
            id=1,
            name="Vernon",
            status="Active",
            node=node,
            latitude=0,
            longitude=0,
        )
        accesspoint.save()

        response = self.c.get(f"/api/v1/accesspoints/{accesspoint.id}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["network_number"], node.network_number)

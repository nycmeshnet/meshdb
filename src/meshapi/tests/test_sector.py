import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Device, Node, Sector
from .sample_data import sample_node


class TestSector(TestCase):
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

    def test_new_sector(self):
        response = self.c.post(
            "/api/v1/sectors/",
            {
                "node": {"id": str(self.node.id)},
                "status": Device.DeviceStatus.ACTIVE,
                "azimuth": 0,
                "width": 120,
                "radius": 0.3,
            },
            content_type="application/json",
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_broken_sector(self):
        response = self.c.post(
            "/api/v1/sectors/",
            {
                "name": "Vernon",
                "node": {"id": str(self.node.id)},
                "latitude": 0,
                "longitude": 0,
                "azimuth": 0,
                "width": 120,
                "radius": 0.3,
            },
            content_type="application/json",
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_get_sector(self):
        node = Node(**sample_node)
        node.save()
        sector = Sector(
            name="Vernon",
            status="Active",
            azimuth=0,
            width=120,
            radius=0.3,
            node=node,
        )
        sector.save()

        response = self.c.get(f"/api/v1/sectors/{sector.id}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["node"]["network_number"], node.network_number)

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
                "node": {"id": str(self.node.id)},
                "status": Device.DeviceStatus.ACTIVE,
                "latitude": 0,
                "longitude": 0,
            },
            content_type="application/json",
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
                "node": {"id": str(self.node.id)},
                "latitude": 0,
                "longitude": 0,
            },
            content_type="application/json",
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
        self.assertEqual(response_obj["node"]["network_number"], node.network_number)
        self.assertEqual(response_obj["node"]["id"], str(node.id))

    def test_modify_latitude(self):
        accesspoint = AccessPoint(
            name="Vernon",
            status="Active",
            node=self.node,
            latitude=0,
            longitude=0,
        )
        accesspoint.save()

        # Modifying latitude should be possible, since it is not read-only
        # (unlike on the Parent Device model)
        response = self.c.patch(
            f"/api/v1/accesspoints/{accesspoint.id}/",
            {"latitude": 22},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        accesspoint.refresh_from_db()
        self.assertEqual(22, accesspoint.latitude)
        self.node.refresh_from_db()
        self.assertEqual(0, self.node.latitude)

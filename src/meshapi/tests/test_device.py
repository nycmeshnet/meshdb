import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Building, Device, Link, Node
from .sample_data import sample_device, sample_node


class TestDevice(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.node1 = Node(**sample_node)
        self.node1.save()

        self.device = Device(**sample_device)
        self.device.node = self.node1
        self.device.save()

    def test_new_device(self):
        response = self.c.post(
            "/api/v1/devices/",
            {
                "model_name": "Lightbeam",
                "status": Device.DeviceStatus.INACTIVE,
                "type": Device.DeviceType.STATION,
                "latitude": 0.0,
                "longitude": 0.0,
                "node": self.node1.network_number,
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_broken_device_node(self):
        response = self.c.post(
            "/api/v1/devices/",
            {
                "model_name": "Lightbeam",
                "status": Device.DeviceStatus.INACTIVE,
                "type": Device.DeviceType.STATION,
                "latitude": 0.0,
                "longitude": 0.0,
                # Missing node
            },
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_broken_device_status(self):
        response = self.c.post(
            "/api/v1/devices/",
            {
                "node": self.node1.network_number,
                "model_name": "Lightbeam",
                "type": Device.DeviceType.STATION,
                "latitude": 0.0,
                "longitude": 0.0,
                # Missing status
            },
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_get_device(self):
        response = self.c.get(f"/api/v1/devices/{self.device.id}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["name"], None)
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], None)

    def test_modify_device(self):
        response = self.c.patch(
            f"/api/v1/devices/{self.device.id}/",
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
        self.assertEqual(response_obj["name"], None)
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], "New notes! Wheee")

    def test_delete_device(self):
        device_id = self.device.id
        response = self.c.delete(f"/api/v1/devices/{device_id}/")

        code = 204
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        self.assertEqual(0, len(Device.objects.filter(id=device_id)))

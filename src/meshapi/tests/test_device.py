import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from rest_framework.authtoken.models import Token

from ..models import Device, Node
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
                "status": Device.DeviceStatus.INACTIVE,
                "node": {"id": str(self.node1.id)},
            },
            content_type="application/json",
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
                "status": Device.DeviceStatus.INACTIVE,
                # Missing node
            },
            content_type="application/json",
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_device_hardware_details(self):
        details = {"model": "Example Model", "ip_address": "10.69.123.45", "type": "aos7"}
        response = self.c.post(
            "/api/v1/devices/",
            {"status": Device.DeviceStatus.ACTIVE, "node": {"id": str(self.node1.id)}, **details},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        device_id = response.json()["id"]
        listing = self.c.get("/api/v1/devices/")
        self.assertEqual(listing.status_code, 200)
        device = next(device for device in listing.json()["results"] if device["id"] == device_id)
        for field, value in details.items():
            self.assertEqual(device[field], value)

        detail_url = f"/api/v1/devices/{device_id}/"
        response = self.c.patch(detail_url, {"ip_address": "2001:db8::10"}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.c.get(detail_url).json()["ip_address"], "2001:db8::10")
        for device_type in ("other", None):
            with self.subTest(device_type=device_type):
                response = self.c.patch(detail_url, {"type": device_type}, content_type="application/json")
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(self.c.get(detail_url).json()["type"], device_type)

    def test_oxidized_feed(self):
        url = "/api/v1/devices/oxidized/"
        self.assertIn(Client().get(url).status_code, (401, 403))

        ipv4 = Device.objects.create(
            node=self.node1, status=Device.DeviceStatus.ACTIVE, name="router-v4", type="ios", ip_address="10.69.123.45"
        )
        ipv6 = Device.objects.create(
            node=self.node1,
            status=Device.DeviceStatus.ACTIVE,
            name="router-v6",
            type="iosxr",
            ip_address="2001:db8::10",
        )
        for status, device_type, address in (
            (Device.DeviceStatus.ACTIVE, "other", "10.69.123.46"),
            (Device.DeviceStatus.ACTIVE, None, "10.69.123.47"),
            (Device.DeviceStatus.ACTIVE, "ios", None),
            (Device.DeviceStatus.INACTIVE, "ios", "10.69.123.48"),
        ):
            Device.objects.create(
                node=self.node1, name="excluded-router", status=status, type=device_type, ip_address=address
            )

        Device.objects.create(node=self.node1, status=Device.DeviceStatus.ACTIVE, type="ios", ip_address="10.69.123.49")

        token = Token.objects.create(user=self.admin_user)
        response = Client().get(url, {"page_size": 1}, HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertCountEqual(
            response.json(),
            [
                {"name": ipv4.name, "ip": "10.69.123.45", "model": "ios"},
                {"name": ipv6.name, "ip": "2001:db8::10", "model": "iosxr"},
            ],
        )

    def test_invalid_hardware_details_are_rejected_on_create_and_update(self):
        for field, value in (
            ("ip_address", "10.69.123.256"),
            ("ip_address", "2001:db8::xyz"),
            ("type", "unknown-driver"),
            ("type", ""),
        ):
            with self.subTest(field=field, value=value):
                response = self.c.post(
                    "/api/v1/devices/",
                    {"status": Device.DeviceStatus.ACTIVE, "node": {"id": str(self.node1.id)}, field: value},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())

                response = self.c.patch(
                    f"/api/v1/devices/{self.device.id}/", {field: value}, content_type="application/json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
                self.device.refresh_from_db()
                self.assertIsNone(getattr(self.device, field))

    def test_broken_device_status(self):
        response = self.c.post(
            "/api/v1/devices/",
            {
                "node": {"id": str(self.node1.id)},
                # Missing status
            },
            content_type="application/json",
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
        self.assertEqual(response_obj["latitude"], 0)  # Read through via the Node Object
        self.assertEqual(response_obj["longitude"], 0)  # Read through via the Node Object
        self.assertEqual(response_obj["altitude"], None)  # Read through via the Node Object

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

    def test_modify_latitude(self):
        # Modifying latitude shouldn't be possible, since it is read-only
        response = self.c.patch(
            f"/api/v1/devices/{self.device.id}/",
            {"latitude": 22},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        self.device.refresh_from_db()
        self.assertEqual(0, self.device.latitude)
        self.node1.refresh_from_db()
        self.assertEqual(0, self.node1.latitude)

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

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Building, Device, Link, Node
from .sample_data import sample_device, sample_node


class TestLink(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.node1 = Node(**sample_node)
        self.node1.save()
        self.node2 = Node(**sample_node)
        self.node2.save()

        self.device1 = Device(**sample_device)
        self.device1.node = self.node1
        self.device1.save()

        self.device2 = Device(**sample_device)
        self.device2.node = self.node2
        self.device2.save()

        self.link = Link(
            from_device=self.device1,
            to_device=self.device2,
            status=Link.LinkStatus.ACTIVE,
        )
        self.link.save()

    def test_new_link(self):
        response = self.c.post(
            "/api/v1/links/",
            {
                "from_device": self.device1.id,
                "to_device": self.device2.id,
                "status": "Active",
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_broken_link(self):
        response = self.c.post(
            "/api/v1/links/",
            {
                "from_building": "",
                "to_building": self.device2.id,
                "status": "Active",
            },
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_get_link(self):
        link = Link(
            from_device=self.device1,
            to_device=self.device2,
            status=Link.LinkStatus.ACTIVE,
        )
        link.save()

        response = self.c.get(f"/api/v1/links/{link.id}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["from_device"], self.device1.id)
        self.assertEqual(response_obj["to_device"], self.device2.id)

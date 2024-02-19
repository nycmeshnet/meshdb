import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Building, Link


class TestLink(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.building_1 = Building(
            id=1,
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            invalid=True,
        )
        self.building_1.save()

        self.building_2 = Building(
            id=2,
            building_status=Building.BuildingStatus.ACTIVE,
            address_truth_sources="",
            latitude=0,
            longitude=0,
            altitude=0,
            invalid=True,
        )
        self.building_2.save()

    def test_new_link(self):
        response = self.c.post(
            "/api/v1/links/",
            {
                "from_building": self.building_1.id,
                "to_building": self.building_2.id,
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
                "to_building": self.building_2.id,
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
            from_building=self.building_1,
            to_building=self.building_2,
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
        self.assertEqual(response_obj["from_building"], 1)
        self.assertEqual(response_obj["to_building"], 2)

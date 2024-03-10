import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Building, Install, Member, Sector

from meshapi.tests.sample_data import sample_building, sample_install, sample_member


class TestSector(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.member_1 = Member(**sample_member)
        self.member_1.save()

        self.building_1 = Building(**sample_building)
        self.building_1.save()

        install = sample_install.copy()
        install["member"] = self.member_1
        install["building"] = self.building_1
        self.install_1 = Install(**install)
        self.install_1.save()

    def test_new_sector(self):
        response = self.c.post(
            "/api/v1/sectors/",
            {
                "name": "Vernon",
                "device_name": "LAP-120",
                "powered_by_install": self.install_1.install_number,
                "status": "Active",
                "azimuth": 0,
                "width": 120,
                "radius": 0.3,
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
            "/api/v1/sectors/",
            {
                "name": "Vernon",
                "device_name": "",
                "powered_by_install": "",
                "status": "",
                "azimuth": 0,
                "width": 120,
                "radius": 0.3,
            },
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_get_sector(self):
        sector = Sector(
            id=1,
            name="Vernon",
            device_name="LAP-120",
            powered_by_install=self.install_1,
            status="Active",
            azimuth=0,
            width=120,
            radius=0.3,
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
        self.assertEqual(response_obj["powered_by_install"], self.install_1.install_number)

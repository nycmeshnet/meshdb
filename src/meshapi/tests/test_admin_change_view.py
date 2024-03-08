from django.test import Client, TestCase
from django.contrib.auth.models import User

from meshapi.models import Building, Device, Install, Link, Member, Sector
from .sample_data import add_sample_data, sample_building, sample_install, sample_member


class TestAdminChangeView(TestCase):
    c = Client()

    def setUp(self):
        (
            self.member,
            self.building_1,
            self.building_2,
            self.install_1,
            self.install_2,
            self.device_1,
            self.device_2,
            self.link,
        ) = add_sample_data()

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def _call(self, route, code):
        response = self.c.get(route)
        self.assertEqual(code, response.status_code, f"Call to admin panel route {route} failed. Got code {code}.")

    def test_change_building(self):
        self._call(f"/admin/meshapi/building/{self.building_1.id}/change/", 200)

    def test_change_member(self):
        self._call(f"/admin/meshapi/member/{self.member.id}/change/", 200)

    def test_change_install(self):
        self._call(f"/admin/meshapi/install/{self.install_1.install_number}/change/", 200)

    def test_change_link(self):
        self._call(f"/admin/meshapi/link/{self.link.id}/change/", 200)

    def test_change_sector(self):
        self._call(f"/admin/meshapi/device/{self.device_1.id}/change/", 200)

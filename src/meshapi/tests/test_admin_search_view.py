from django.test import Client, TestCase
from django.contrib.auth.models import User

from meshapi.models import Building, Install, Link, Member, Sector
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

    def test_search_building(self):
        self._call("/admin/meshapi/building/?q=1", 200)

    def test_search_member(self):
        self._call("/admin/meshapi/member/?q=1", 200)

    def test_search_install(self):
        self._call("/admin/meshapi/install/?q=1", 200)

    def test_search_link(self):
        self._call("/admin/meshapi/link/?q=1", 200)

    def test_search_device(self):
        self._call("/admin/meshapi/device/?q=1", 200)

    def test_search_sector(self):
        self._call("/admin/meshapi/sector/?q=1", 200)

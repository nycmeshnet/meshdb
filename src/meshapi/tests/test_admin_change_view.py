from django.test import Client, TestCase
from django.contrib.auth.models import User

from meshapi.models import Building, Install, Link, Member, Sector
from .sample_data import sample_building, sample_install, sample_member


class TestAdminChangeView(TestCase):
    c = Client()

    def setUp(self):
        sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        sample_install_copy["building"] = self.building_1

        self.building_2 = Building(**sample_building)
        self.building_2.street_address = "69" + str(self.building_2.street_address)
        self.building_2.save()

        self.member = Member(**sample_member)
        self.member.save()
        sample_install_copy["member"] = self.member

        self.install = Install(**sample_install_copy)
        self.install.save()

        self.sector = Sector(
            id=1,
            name="Vernon",
            device_name="LAP-120",
            building=self.building_1,
            status="Active",
            azimuth=0,
            width=120,
            radius=0.3,
        )
        self.sector.save()

        self.link = Link(
            from_building=self.building_1,
            to_building=self.building_2,
            status=Link.LinkStatus.ACTIVE,
        )
        self.link.save()

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
        self._call(f"/admin/meshapi/install/{self.install.install_number}/change/", 200)

    def test_change_link(self):
        self._call(f"/admin/meshapi/link/{self.link.id}/change/", 200)

    def test_change_sector(self):
        self._call(f"/admin/meshapi/sector/{self.sector.id}/change/", 200)

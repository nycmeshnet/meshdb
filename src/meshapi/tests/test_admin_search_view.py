from django.contrib.auth.models import User
from django.test import Client, TestCase

from meshapi.models import Building, Device, Install, Link, Member, Node, Sector

from .sample_data import sample_building, sample_device, sample_install, sample_member, sample_node


class TestAdminSearchView(TestCase):
    c = Client()

    def setUp(self):
        sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        sample_install_copy["building"] = self.building_1

        self.member = Member(**sample_member)
        self.member.save()
        sample_install_copy["member"] = self.member

        self.install = Install(**sample_install_copy)
        self.install.save()

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

        self.sector = Sector(
            radius=1,
            azimuth=45,
            width=180,
            **sample_device,
        )
        self.sector.node = self.node2
        self.sector.save()

        self.link = Link(
            from_device=self.device1,
            to_device=self.device2,
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

    def test_search_building(self):
        self._call("/admin/meshapi/building/?q=1", 200)

    def test_search_member(self):
        self._call("/admin/meshapi/member/?q=1", 200)

    def test_search_install(self):
        self._call("/admin/meshapi/install/?q=1", 200)

    def test_search_link(self):
        self._call("/admin/meshapi/link/?q=1", 200)

    def test_search_sector(self):
        self._call("/admin/meshapi/sector/?q=1", 200)

    def test_search_device(self):
        self._call("/admin/meshapi/device/?q=1", 200)

    def test_search_node(self):
        self._call("/admin/meshapi/node/?q=1", 200)

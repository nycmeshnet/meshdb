from django.contrib.auth.models import User
from django.test import Client, TestCase

from meshapi.models import Building, Device, Install, Link, Member, Node, Sector

from .sample_data import sample_building, sample_device, sample_install, sample_member, sample_node


class TestAdminChangeView(TestCase):
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

    def test_change_building(self):
        self._call(f"/admin/meshapi/building/{self.building_1.id}/change/", 200)

    def test_change_member(self):
        self._call(f"/admin/meshapi/member/{self.member.id}/change/", 200)

    def test_change_install(self):
        self._call(f"/admin/meshapi/install/{self.install.install_number}/change/", 200)

    def test_change_link(self):
        self._call(f"/admin/meshapi/link/{self.link.id}/change/", 200)

    def test_change_device(self):
        self._call(f"/admin/meshapi/device/{self.device1.id}/change/", 200)

    def test_change_node(self):
        self._call(f"/admin/meshapi/node/{self.node1.network_number}/change/", 200)

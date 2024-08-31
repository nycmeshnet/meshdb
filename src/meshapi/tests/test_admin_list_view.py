import datetime

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from rest_framework.authtoken.models import TokenProxy

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector
from meshapi.tests.sample_data import sample_building, sample_device, sample_install, sample_member, sample_node
from meshapi.tests.util import get_admin_results_count
from meshapi_hooks.hooks import CelerySerializerHook


# Sanity check to make sure that the list views in the admin panel still work
# These will often break when you update something in the model and forget to
# update the admin panel
class TestAdminListView(TestCase):
    c = Client()

    def setUp(self):
        sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        sample_install_copy["building"] = self.building_1

        self.building_2 = Building(**sample_building)
        self.building_2.save()

        self.los = LOS(
            from_building=self.building_1,
            to_building=self.building_2,
            analysis_date=datetime.date(2024, 1, 1),
            source=LOS.LOSSource.HUMAN_ANNOTATED,
        )
        self.los.save()

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

        self.access_point = AccessPoint(
            **sample_device,
            latitude=0,
            longitude=0,
        )
        self.access_point.node = self.node2
        self.access_point.save()

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

        self.test_group = Group.objects.create(name="Test group")

        self.test_auth_token = TokenProxy.objects.create(user=self.admin_user)

        self.test_webhook = CelerySerializerHook.objects.create(
            user=self.admin_user, target="http://example.com", event="building.created", headers=""
        )

    def _call(self, route, code):
        response = self.c.get(route)
        self.assertEqual(code, response.status_code, f"Could not view {route} in the admin panel.")
        return response

    def test_list_group(self):
        response = self._call("/admin/auth/group/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_user(self):
        response = self._call("/admin/auth/user/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_authtoken(self):
        response = self._call("/admin/authtoken/tokenproxy/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_hook(self):
        response = self._call("/admin/meshapi_hooks/celeryserializerhook/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_building(self):
        response = self._call("/admin/meshapi/building/", 200)
        self.assertEqual(2, get_admin_results_count(response.content.decode()))

    def test_list_member(self):
        response = self._call("/admin/meshapi/member/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_install(self):
        response = self._call("/admin/meshapi/install/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_link(self):
        response = self._call("/admin/meshapi/link/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_los(self):
        response = self._call("/admin/meshapi/los/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_sector(self):
        response = self._call("/admin/meshapi/sector/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_accesspoint(self):
        response = self._call("/admin/meshapi/accesspoint/", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_list_device(self):
        response = self._call("/admin/meshapi/device/", 200)
        self.assertEqual(2, get_admin_results_count(response.content.decode()))

    def test_list_node(self):
        response = self._call("/admin/meshapi/node/", 200)
        self.assertEqual(2, get_admin_results_count(response.content.decode()))

import datetime

from django.contrib.auth.models import User
from django.test import Client, TestCase

from meshapi.models import (
    LOS,
    AccessPoint,
    Building,
    Device,
    Install,
    InstallFeeBillingDatum,
    Link,
    Member,
    Node,
    Sector,
)

from .sample_data import sample_building, sample_device, sample_install, sample_member, sample_node
from .util import get_admin_results_count


class TestAdminSearchView(TestCase):
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
        self.install.referral = "reddit or something, I don't remember"
        self.install.save()

        self.billing_datum = InstallFeeBillingDatum(
            install=self.install,
        )
        self.billing_datum.save()

        self.node1 = Node(**sample_node)
        self.node1.save()

        self.building_1.primary_node = self.node1
        self.building_1.save()

        self.node2 = Node(**sample_node)
        self.node2.save()

        self.install.node = self.node1
        self.install.save()

        self.building_2.primary_node = self.node2
        self.building_2.save()

        self.device1 = Device(
            **sample_device,
            name="Device1",
        )
        self.device1.node = self.node1
        self.device1.save()

        self.device2 = Device(
            **sample_device,
            name="Device2",
        )
        self.device2.node = self.node2
        self.device2.save()

        self.sector = Sector(
            name="Sector1",
            radius=1,
            azimuth=45,
            width=180,
            **sample_device,
        )
        self.sector.node = self.node2
        self.sector.save()

        self.access_point = AccessPoint(
            **sample_device,
            name="AP1",
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

    def _call(self, route, code):
        response = self.c.get(route)
        self.assertEqual(code, response.status_code, f"Call to admin panel route {route} failed. Got code {code}.")
        return response

    def test_search_building(self):
        response = self._call("/admin/meshapi/building/?q=8888", 200)
        self.assertEqual(2, get_admin_results_count(response.content.decode()))

    def test_search_member(self):
        response = self._call("/admin/meshapi/member/?q=1", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_install(self):
        response = self._call(f"/admin/meshapi/install/?q={self.install.install_number}", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_installfeebillingdatum(self):
        response = self._call(f"/admin/meshapi/installfeebillingdatum/?q={self.install.install_number}", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_link(self):
        response = self._call("/admin/meshapi/link/?q=101", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_los(self):
        response = self._call("/admin/meshapi/los/?q=101", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_sector(self):
        response = self._call("/admin/meshapi/sector/?q=1", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_access_point(self):
        response = self._call("/admin/meshapi/accesspoint/?q=1", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_device(self):
        response = self._call("/admin/meshapi/device/?q=1", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_node(self):
        response = self._call("/admin/meshapi/node/?q=101", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_install_by_nn(self):
        response = self._call("/admin/meshapi/install/?q=101", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_install_by_nn_exact(self):
        # This install should be matched by the below query, because of the NN101 note.
        # (in addition to self.install)
        sample_install_copy = sample_install.copy()
        install2 = Install(**sample_install_copy)
        install2.building = self.building_2
        install2.member = self.member
        install2.notes = "NN101"
        install2.save()

        response = self._call("/admin/meshapi/install/?q=NN101", 200)
        self.assertEqual(2, get_admin_results_count(response.content.decode()))

    def test_search_install_just_nn(self):
        response = self._call("/admin/meshapi/install/?q=nN", 200)
        self.assertEqual(0, get_admin_results_count(response.content.decode()))

    def test_search_install_empty(self):
        response = self._call("/admin/meshapi/install/?q=", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

    def test_search_install_referral(self):
        response = self._call("/admin/meshapi/install/?q=reddit", 200)
        self.assertEqual(1, get_admin_results_count(response.content.decode()))

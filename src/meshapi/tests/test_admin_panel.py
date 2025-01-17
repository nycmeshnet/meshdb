import datetime

from bs4 import BeautifulSoup
from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from rest_framework.authtoken.models import TokenProxy

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector
from meshapi.tests.sample_data import sample_building, sample_device, sample_install, sample_member, sample_node
from meshapi_hooks.hooks import CelerySerializerHook


class TestAdminPanel(TestCase):
    c = Client()

    def setUp(self) -> None:
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

    def test_iframe_loads(self):
        route = "/admin/iframe_wrapper/"
        code = 200
        response = self.c.get(route)
        self.assertEqual(code, response.status_code, f"Could not view {route} in the admin panel.")

        decoded_panel = response.content.decode()
        soup = BeautifulSoup(decoded_panel, "html.parser")
        iframe = soup.find(id="admin_panel_iframe")
        iframe_src = iframe.attrs["src"]
        self.assertEqual("/admin/", iframe_src)
        iframe_response = self.c.get(iframe_src)
        self.assertEqual(code, iframe_response.status_code, f"Could not view {route} in the admin panel.")

    # TODO (wdn): Add more tests checking if navigating to xyz page works
    # Unfortunately, because that is a lot of javascript, it's tricky to test.
    # It may be possible to run selenium integration tests or something to validate
    # that functionality

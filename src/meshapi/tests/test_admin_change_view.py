import datetime

import bs4
from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from rest_framework.authtoken.models import TokenProxy

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector
from meshapi_hooks.hooks import CelerySerializerHook

from .sample_data import sample_building, sample_device, sample_install, sample_member, sample_node


class TestAdminChangeView(TestCase):
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
        self.assertEqual(code, response.status_code, f"Call to admin panel route {route} failed. Got code {code}.")
        return response

    def _submit_form(self, route, form: bs4.Tag, code):
        inputs = form.find_all("input")

        form_data = {}
        for input_tag in inputs:
            name = input_tag.get("name")
            value = input_tag.get("value", "")
            if name is not None:
                form_data[name] = value

        for select_tag in form.find_all("select"):
            name = select_tag.get("name")
            selected_option = select_tag.find("option", selected=True)
            if selected_option:
                value = selected_option.get("value")
            else:
                # If no option is explicitly selected, take the first one
                # (this seems wrong, but it's correct, HTML select forms are weird)
                first_option_tag = select_tag.find("option")
                if first_option_tag:
                    value = first_option_tag.get("value")
                else:
                    value = None

            if value:
                form_data[name] = value

        form_data["_save"] = "Save"
        del form_data["_addanother"]
        del form_data["_continue"]
        del form_data["_export-item"]

        response = self.c.post(route, data=form_data)
        response_soup = bs4.BeautifulSoup(response.content.decode(), "html.parser")
        response_forms = response_soup.find_all("form")
        self.assertEqual(
            0,
            len(response_soup.findAll(class_="errornote")),
            f"Expected no errors on page, make sure editing works on {route}. Form contents: "
            f"{response_forms[1].prettify() if len(response_forms) > 1 else 'None'}",
        )
        self.assertEqual(
            code,
            response.status_code,
            f"Call to admin panel route {route} failed. Got code {code}. "
            f"Response body: {response.content.decode()}",
        )
        return response

    def test_change_building(self):
        change_url = f"/admin/meshapi/building/{self.building_1.id}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="building_form"), 302)

    def test_change_member(self):
        change_url = f"/admin/meshapi/member/{self.member.id}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="member_form"), 302)

    def test_change_install(self):
        change_url = f"/admin/meshapi/install/{self.install.install_number}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="install_form"), 302)

    def test_change_link(self):
        change_url = f"/admin/meshapi/link/{self.link.id}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="link_form"), 302)

    def test_change_los(self):
        change_url = f"/admin/meshapi/los/{self.los.id}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="los_form"), 302)

    def test_change_device(self):
        change_url = f"/admin/meshapi/device/{self.device1.id}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="device_form"), 302)

    def test_change_sector(self):
        change_url = f"/admin/meshapi/sector/{self.sector.id}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="sector_form"), 302)

    def test_change_accesspoint(self):
        change_url = f"/admin/meshapi/accesspoint/{self.access_point.id}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="accesspoint_form"), 302)

    def test_change_node(self):
        change_url = f"/admin/meshapi/node/{self.node1.network_number}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="node_form"), 302)

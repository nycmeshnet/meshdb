import datetime
import json
from typing import Dict, Optional

import bs4
from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from flags.state import enable_flag
from rest_framework.authtoken.models import TokenProxy

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector
from meshapi_hooks.hooks import CelerySerializerHook
from meshdb.utils.spreadsheet_import.building.constants import AddressTruthSource

from .sample_data import sample_building, sample_device, sample_install, sample_member, sample_node


def fill_in_admin_form(soup: bs4.BeautifulSoup, form_data: Dict[str, str]) -> None:
    for tag_id, value in form_data.items():
        tag = soup.find(id=tag_id)
        if tag.name == "input":
            tag["value"] = value
        if tag.name == "textarea":
            tag.string = value
        elif tag.name == "select":
            for option in tag.find_all("option"):
                del option["selected"]

            tag.find("option", value=value)["selected"] = ""


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

        self.member2 = Member(name="Test Member")
        self.member2.save()

        self.install = Install(**sample_install_copy)
        self.install.save()

        self.node1 = Node(**sample_node)
        self.node1.save()
        self.node1.buildings.add(self.building_1)
        self.node2 = Node(**sample_node)
        self.node2.save()
        self.node2.buildings.add(self.building_1)

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
        self.assertEqual(
            code, response.status_code, f"Call to admin panel route {route} failed. Got code {response.status_code}."
        )
        return response

    def _submit_form(
        self,
        route: str,
        form: bs4.Tag,
        code: int,
        additional_form_data: Optional[Dict[str, str]] = None,
        expect_failure=False,
    ):
        inputs = form.find_all("input")

        form_data = {}
        for input_tag in inputs:
            name = input_tag.get("name")
            value = input_tag.get("value", "")
            if name is not None:
                form_data[name] = value

        for textarea_tag in form.find_all("textarea"):
            name = textarea_tag.get("name")
            value = textarea_tag.text
            if textarea_tag.get("data-django-jsonform") and value == "":
                value = json.loads(textarea_tag.get("data-django-jsonform"))["data"]
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

        del form_data["_save"]
        del form_data["_addanother"]
        form_data["_continue"] = "Save and continue editing"
        if "_export-item" in form_data:
            del form_data["_export-item"]

        if additional_form_data:
            for key, value in additional_form_data.items():
                form_data[key] = value

        response = self.c.post(route, data=form_data)
        response_soup = bs4.BeautifulSoup(response.content.decode(), "html.parser")
        response_forms = response_soup.find_all("form")
        assertion_func = self.assertEqual

        if expect_failure:
            assertion_func = self.assertGreater

        assertion_func(
            len(response_soup.findAll(class_="errornote")),
            0,
            f"Expected{'' if expect_failure else ' no'} errors on page, check editing on {route}. Form contents: "
            f"{response_forms[1].prettify() if len(response_forms) > 1 else 'None'}",
        )
        self.assertEqual(
            code,
            response.status_code,
            f"Call to admin panel route {route} failed. Got code {response.status_code}. "
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

    def test_change_member_no_email(self):
        change_url = f"/admin/meshapi/member/{self.member2.id}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="member_form"), 302)

        self.member2.refresh_from_db()
        self.assertIsNone(self.member2.primary_email_address)

    def test_add_new_member(self):
        change_url = "/admin/meshapi/member/add/"
        response = self._call(change_url, 200)
        form_soup = bs4.BeautifulSoup(response.content.decode()).find(id="member_form")
        fill_in_admin_form(
            form_soup,
            {
                "id_name": "Test Member",
                "id_primary_email_address": "test1@example.com",
                "id_stripe_email_address": "test2@example.com",
                "id_additional_email_addresses": json.dumps(["test3@example.com", "test4@example.com"]),
                "id_phone_number": "+1 123 555 5555",
                "id_additional_phone_numbers": json.dumps(["+1 123 555 5566", "+1 123 555 5577"]),
                "id_slack_handle": "abcdef",
                "id_notes": "Test notes",
            },
        )

        response = self._submit_form(change_url, form_soup, 302)
        member_id = response.url.split("/")[-3]
        member = Member.objects.get(id=member_id)

        self.assertEqual(member.name, "Test Member")
        self.assertEqual(member.primary_email_address, "test1@example.com")
        self.assertEqual(member.stripe_email_address, "test2@example.com")
        self.assertEqual(member.additional_email_addresses, ["test3@example.com", "test4@example.com"])
        self.assertEqual(member.phone_number, "+1 1235555555")
        self.assertEqual(member.additional_phone_numbers, ["+1 1235555566", "+1 1235555577"])
        self.assertEqual(member.slack_handle, "abcdef")
        self.assertEqual(member.notes, "Test notes")

    def test_add_new_member_name_only(self):
        change_url = "/admin/meshapi/member/add/"
        response = self._call(change_url, 200)
        form_soup = bs4.BeautifulSoup(response.content.decode()).find(id="member_form")
        fill_in_admin_form(
            form_soup,
            {
                "id_name": "Test Member",
            },
        )

        response = self._submit_form(change_url, form_soup, 302)
        member_id = response.url.split("/")[-3]
        member = Member.objects.get(id=member_id)

        self.assertEqual(member.name, "Test Member")
        self.assertIsNone(member.primary_email_address)
        self.assertIsNone(member.stripe_email_address)
        self.assertEqual(member.additional_email_addresses, [])
        self.assertIsNone(member.phone_number)
        self.assertEqual(member.additional_phone_numbers, [])
        self.assertIsNone(member.slack_handle)
        self.assertEqual(member.notes, "")

    def test_change_install(self):
        change_url = f"/admin/meshapi/install/{self.install.id}/change/"
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
        change_url = f"/admin/meshapi/node/{self.node1.id}/change/"
        response = self._call(change_url, 200)
        self._submit_form(change_url, bs4.BeautifulSoup(response.content.decode()).find(id="node_form"), 302)

    def test_change_node_remove_building(self):
        change_url = f"/admin/meshapi/node/{self.node1.id}/change/"
        response = self._call(change_url, 200)
        soup = bs4.BeautifulSoup(response.content.decode()).find(id="node_form")
        fill_in_admin_form(
            soup,
            {
                "id_Building_nodes-0-DELETE": "on",
            },
        )

        # Deselecting all buildings for the node should result in a validation failure
        self._submit_form(change_url, soup, 200, expect_failure=True)

    def test_add_new_node(self):
        change_url = "/admin/meshapi/node/add/"
        response = self._call(change_url, 200)
        form_soup = bs4.BeautifulSoup(response.content.decode()).find(id="node_form")
        fill_in_admin_form(
            form_soup,
            {
                "id_network_number": "123",
                "id_status": "Active",
                "id_type": "Standard",
                "id_name": "Test Node",
                "id_latitude": "0",
                "id_longitude": "0",
                "id_altitude": "0",
                "id_install_date": "2022-02-23",
                "id_abandon_date": "2022-02-23",
                "id_notes": "Test notes",
            },
        )

        additional_form_data = {
            "Building_nodes-TOTAL_FORMS": "1",
            "Building_nodes-INITIAL_FORMS": "0",
            "Building_nodes-0-id": "",
            "Building_nodes-0-node": "",
            "Building_nodes-0-building": str(self.building_1.id),
        }

        response = self._submit_form(change_url, form_soup, 302, additional_form_data)
        node_id = response.url.split("/")[-3]
        node = Node.objects.get(id=node_id)

        self.assertEqual(node.network_number, 123)
        self.assertEqual(node.status, Node.NodeStatus.ACTIVE)
        self.assertEqual(node.type, Node.NodeType.STANDARD)
        self.assertEqual(node.name, "Test Node")
        self.assertEqual(node.latitude, 0)
        self.assertEqual(node.longitude, 0)
        self.assertEqual(node.altitude, 0)
        self.assertEqual(node.install_date, datetime.date(2022, 2, 23))
        self.assertEqual(node.abandon_date, datetime.date(2022, 2, 23))
        self.assertEqual(node.notes, "Test notes")

    def test_add_new_node_no_building(self):
        change_url = "/admin/meshapi/node/add/"
        response = self._call(change_url, 200)
        form_soup = bs4.BeautifulSoup(response.content.decode()).find(id="node_form")
        fill_in_admin_form(
            form_soup,
            {
                "id_network_number": "123",
                "id_status": "Active",
                "id_type": "Standard",
                "id_name": "Test Node",
                "id_latitude": "0",
                "id_longitude": "0",
                "id_altitude": "0",
                "id_install_date": "2022-02-23",
                "id_abandon_date": "2022-02-23",
                "id_notes": "Test notes",
            },
        )

        # Not selecting a building for the new node should result in a validation failure
        self._submit_form(change_url, form_soup, 200, expect_failure=True)

    def test_add_new_node_no_nn(self):
        change_url = "/admin/meshapi/node/add/"
        response = self._call(change_url, 200)
        form_soup = bs4.BeautifulSoup(response.content.decode()).find(id="node_form")
        fill_in_admin_form(
            form_soup,
            {
                "id_status": "Active",
                "id_type": "Standard",
                "id_name": "Test Node",
                "id_latitude": "0",
                "id_longitude": "0",
                "id_altitude": "0",
                "id_install_date": "2022-02-23",
                "id_abandon_date": "2022-02-23",
                "id_notes": "Test notes",
            },
        )

        additional_form_data = {
            "Building_nodes-TOTAL_FORMS": "1",
            "Building_nodes-INITIAL_FORMS": "0",
            "Building_nodes-0-id": "",
            "Building_nodes-0-node": "",
            "Building_nodes-0-building": str(self.building_1.id),
        }

        response = self._submit_form(change_url, form_soup, 302, additional_form_data)
        node_id = response.url.split("/")[-3]
        node = Node.objects.get(id=node_id)

        self.assertIsNotNone(node.network_number)
        self.assertEqual(node.status, Node.NodeStatus.ACTIVE)
        self.assertEqual(node.type, Node.NodeType.STANDARD)
        self.assertEqual(node.name, "Test Node")
        self.assertEqual(node.latitude, 0)
        self.assertEqual(node.longitude, 0)
        self.assertEqual(node.altitude, 0)
        self.assertEqual(node.install_date, datetime.date(2022, 2, 23))
        self.assertEqual(node.abandon_date, datetime.date(2022, 2, 23))
        self.assertEqual(node.notes, "Test notes")

    def test_add_new_planned_node_no_nn(self):
        change_url = "/admin/meshapi/node/add/"
        response = self._call(change_url, 200)
        form_soup = bs4.BeautifulSoup(response.content.decode()).find(id="node_form")
        fill_in_admin_form(
            form_soup,
            {
                "id_status": "Planned",
                "id_type": "Standard",
                "id_name": "Test Node",
                "id_latitude": "0",
                "id_longitude": "0",
                "id_altitude": "0",
                "id_install_date": "2022-02-23",
                "id_abandon_date": "2022-02-23",
                "id_notes": "Test notes",
            },
        )

        additional_form_data = {
            "Building_nodes-TOTAL_FORMS": "1",
            "Building_nodes-INITIAL_FORMS": "0",
            "Building_nodes-0-id": "",
            "Building_nodes-0-node": "",
            "Building_nodes-0-building": str(self.building_1.id),
        }

        response = self._submit_form(change_url, form_soup, 302, additional_form_data)
        node_id = response.url.split("/")[-3]
        node = Node.objects.get(id=node_id)

        self.assertIsNone(node.network_number)
        self.assertEqual(node.status, Node.NodeStatus.PLANNED)
        self.assertEqual(node.type, Node.NodeType.STANDARD)
        self.assertEqual(node.name, "Test Node")
        self.assertEqual(node.latitude, 0)
        self.assertEqual(node.longitude, 0)
        self.assertEqual(node.altitude, 0)
        self.assertEqual(node.install_date, datetime.date(2022, 2, 23))
        self.assertEqual(node.abandon_date, datetime.date(2022, 2, 23))
        self.assertEqual(node.notes, "Test notes")

    def test_add_building(self):
        enable_flag("EDIT_PANORAMAS")
        change_url = "/admin/meshapi/building/add/"
        response = self._call(change_url, 200)
        form_soup = bs4.BeautifulSoup(response.content.decode()).find(id="building_form")

        fill_in_admin_form(
            form_soup,
            {
                "id_street_address": "123 Test Street",
                "id_city": "New York",
                "id_state": "NY",
                "id_zip_code": "10001",
                "id_bin": "12345678",
                "id_latitude": "0",
                "id_longitude": "0",
                "id_altitude": "0",
                "id_notes": "Test notes",
                "id_panoramas": json.dumps(["http://example.com"]),
                "id_primary_node": str(self.node1.id),
                # "id_nodes": "Test notes",
            },
        )
        response = self._submit_form(change_url, form_soup, 302)
        building_id = response.url.split("/")[-3]
        building = Building.objects.get(id=building_id)

        self.assertEqual(building.street_address, "123 Test Street")
        self.assertEqual(building.city, "New York")
        self.assertEqual(building.state, "NY")
        self.assertEqual(building.zip_code, "10001")
        self.assertEqual(building.bin, 12345678)
        self.assertEqual(building.latitude, 0)
        self.assertEqual(building.longitude, 0)
        self.assertEqual(building.altitude, 0)
        self.assertEqual(building.notes, "Test notes")
        self.assertEqual(building.panoramas, ["http://example.com"])
        self.assertEqual(building.address_truth_sources, [AddressTruthSource.HumanEntry.value])
        self.assertEqual(building.primary_node, self.node1)
        self.assertEqual(list(building.nodes.all()), [self.node1])

    def test_change_building_but_not_address(self):
        enable_flag("EDIT_PANORAMAS")
        change_url = f"/admin/meshapi/building/{self.building_1.id}/change/"
        response = self._call(change_url, 200)
        form_soup = bs4.BeautifulSoup(response.content.decode()).find(id="building_form")
        fill_in_admin_form(
            form_soup,
            {
                "id_street_address": self.building_1.street_address,
                "id_city": self.building_1.city,
                "id_state": self.building_1.state,
                "id_zip_code": str(self.building_1.zip_code),
                "id_bin": "12345678",
                "id_latitude": "0",
                "id_longitude": "0",
                "id_altitude": "0",
                "id_notes": "Test notes",
                "id_panoramas": json.dumps(["http://example.com"]),
                "id_primary_node": str(self.node1.id),
                # "id_nodes": "Test notes",
            },
        )
        response = self._submit_form(change_url, form_soup, 302)
        building_id = response.url.split("/")[-3]
        building = Building.objects.get(id=building_id)

        self.assertEqual(building.street_address, "3333 Chom St")
        self.assertEqual(building.city, "Brooklyn")
        self.assertEqual(building.state, "NY")
        self.assertEqual(building.zip_code, "11111")
        self.assertEqual(building.bin, 12345678)
        self.assertEqual(building.latitude, 0)
        self.assertEqual(building.longitude, 0)
        self.assertEqual(building.altitude, 0)
        self.assertEqual(building.notes, "Test notes")
        self.assertEqual(building.panoramas, ["http://example.com"])
        self.assertEqual(building.address_truth_sources, [AddressTruthSource.NYCPlanningLabs.value])
        self.assertEqual(building.primary_node, self.node1)
        self.assertEqual(list(building.nodes.all()), [self.node1])

    def test_change_building_address(self):
        enable_flag("EDIT_PANORAMAS")
        change_url = f"/admin/meshapi/building/{self.building_1.id}/change/"
        response = self._call(change_url, 200)
        form_soup = bs4.BeautifulSoup(response.content.decode()).find(id="building_form")
        fill_in_admin_form(
            form_soup,
            {
                "id_street_address": "666 ABC St",
                "id_city": "New York",
                "id_state": "NY",
                "id_zip_code": "10001",
                "id_bin": "12345678",
                "id_latitude": "0",
                "id_longitude": "0",
                "id_altitude": "0",
                "id_notes": "Test notes",
                "id_panoramas": json.dumps(["http://example.com"]),
                "id_primary_node": str(self.node1.id),
                # "id_nodes": "Test notes",
            },
        )
        response = self._submit_form(change_url, form_soup, 302)
        building_id = response.url.split("/")[-3]
        building = Building.objects.get(id=building_id)

        self.assertEqual(building.street_address, "666 ABC St")
        self.assertEqual(building.city, "New York")
        self.assertEqual(building.state, "NY")
        self.assertEqual(building.zip_code, "10001")
        self.assertEqual(building.bin, 12345678)
        self.assertEqual(building.latitude, 0)
        self.assertEqual(building.longitude, 0)
        self.assertEqual(building.altitude, 0)
        self.assertEqual(building.notes, "Test notes")
        self.assertEqual(building.panoramas, ["http://example.com"])
        self.assertEqual(
            building.address_truth_sources,
            [AddressTruthSource.NYCPlanningLabs.value, AddressTruthSource.HumanEntry.value],
        )
        self.assertEqual(building.primary_node, self.node1)
        self.assertEqual(list(building.nodes.all()), [self.node1])


class TestAdminAddView(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.client.login(username="admin", password="admin_password")

    def _call(self, route, code):
        response = self.client.get(route)
        self.assertEqual(code, response.status_code, f"Could not view {route} in the admin panel.")
        return response

    def test_add_views_http_200(self):
        self._call("/admin/auth/group/add/", 200)
        self._call("/admin/auth/user/add/", 200)
        self._call("/admin/authtoken/tokenproxy/add/", 200)
        self._call("/admin/meshapi_hooks/celeryserializerhook/add/", 200)
        self._call("/admin/meshapi/building/add/", 200)
        self._call("/admin/meshapi/member/add/", 200)
        self._call("/admin/meshapi/install/add/", 200)
        self._call("/admin/meshapi/link/add/", 200)
        self._call("/admin/meshapi/los/add/", 200)
        self._call("/admin/meshapi/sector/add/", 200)
        self._call("/admin/meshapi/device/add/", 200)
        self._call("/admin/meshapi/accesspoint/add/", 200)
        self._call("/admin/meshapi/node/add/", 200)

import json

from django.conf import os
from django.test import Client, TestCase

from meshapi.models import Building, Install, Member, Node

from .sample_data import sample_building, sample_install, sample_member


class TestQueryForm(TestCase):
    c = Client()

    def setUp(self):
        sample_install_copy = sample_install.copy()
        building = Building(**sample_building)
        building.save()
        sample_install_copy["building"] = building

        member = Member(**sample_member)
        member.save()
        sample_install_copy["member"] = member

        node = Node(latitude=0, longitude=0, status=Node.NodeStatus.ACTIVE)
        node.save()

        self.install = Install(**sample_install_copy)
        self.install.node = node
        self.install.save()

    def query(self, route, field, data):
        code = 200
        password = os.environ.get("QUERY_PSK")
        route = f"/api/v1/query/{route}/?{field}={data}"
        headers = {"Authorization": f"Bearer {password}"}
        response = self.c.get(route, headers=headers)
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
        )

        resp_json = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(resp_json["results"]), 1)

    def test_query_address(self):
        self.query("buildings", "street_address", self.install.building.street_address)

    def test_query_email(self):
        self.query("members", "email_address", self.install.member.primary_email_address)

    def test_query_name(self):
        self.query("members", "name", self.install.member.name)

    def test_query_nn(self):
        self.query("installs", "network_number", self.install.node.network_number)

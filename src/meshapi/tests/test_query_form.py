import json
from django.conf import os

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase

from meshapi.models import Building, Install, Member

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

        self.install = Install(**sample_install_copy)
        self.install.save()

    def query(self, route, field, data):
        code = 200
        password=os.environ.get("QUERY_PSK")
        route = f"/api/v1/query/{route}/?{field}={data}&password={password}"
        response = self.c.get(route)
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
        )

        resp_json = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(resp_json), 1)

    def test_query_address(self):
        self.query("building", "street_address", self.install.building.street_address)

    def test_query_email(self):
        self.query("member", "email_address", self.install.member.email_address)

    def test_query_nn(self):
        self.query("install", "network_number", self.install.network_number)

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from meshapi.tests.sample_data import sample_member

from ..models import Member


class TestPagination(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def test_member_list_pagination(self):
        for i in range(999):
            member = Member(**sample_member)
            member.save()

        response = self.c.get("/api/v1/members/")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)

        self.assertEqual(len(response_obj["results"]), 100)
        self.assertEqual(response_obj["count"], 999)
        self.assertEqual(response_obj["previous"], None)
        self.assertEqual(response_obj["next"], "http://testserver/api/v1/members/?page=2")

        response = self.c.get("/api/v1/members/?page=2")
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)

        self.assertEqual(len(response_obj["results"]), 100)
        self.assertEqual(response_obj["count"], 999)
        self.assertEqual(response_obj["previous"], "http://testserver/api/v1/members/")
        self.assertEqual(response_obj["next"], "http://testserver/api/v1/members/?page=3")

        response = self.c.get("/api/v1/members/?page_size=999999")
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)

        self.assertEqual(len(response_obj["results"]), 999)
        self.assertEqual(response_obj["count"], 999)
        self.assertEqual(response_obj["previous"], None)
        self.assertEqual(response_obj["next"], None)

    def test_member_lookup_pagination(self):
        for i in range(999):
            member = Member(**sample_member)
            member.save()

        response = self.c.get("/api/v1/members/lookup/?name=John+Smith")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)

        self.assertEqual(len(response_obj["results"]), 100)
        self.assertEqual(response_obj["count"], 999)
        self.assertEqual(response_obj["previous"], None)
        self.assertEqual(response_obj["next"], "http://testserver/api/v1/members/lookup/?name=John+Smith&page=2")

        response = self.c.get("/api/v1/members/lookup/?name=John+Smith&page=2")
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)

        self.assertEqual(len(response_obj["results"]), 100)
        self.assertEqual(response_obj["count"], 999)
        self.assertEqual(response_obj["previous"], "http://testserver/api/v1/members/lookup/?name=John+Smith")
        self.assertEqual(response_obj["next"], "http://testserver/api/v1/members/lookup/?name=John+Smith&page=3")

        response = self.c.get("/api/v1/members/lookup/?name=John+Smith&page_size=999999")
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)

        self.assertEqual(len(response_obj["results"]), 999)
        self.assertEqual(response_obj["count"], 999)
        self.assertEqual(response_obj["previous"], None)
        self.assertEqual(response_obj["next"], None)

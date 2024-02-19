import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Member
from .sample_data import sample_member


class TestMemberLookups(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        m1 = Member(**sample_member)
        m1.save()

        m2 = Member(
            name="Donald Smith",
            primary_email_address="donald.smith@example.com",
            stripe_email_address="donny.stripe@example.com",
            additional_email_addresses=["donny.addl@example.com"],
            phone_number="555-555-6666",
        )
        m2.save()

    def test_member_name_search(self):
        response = self.c.get("/api/v1/members/lookup/?name=Joh")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(response_objs[0]["name"], "John Smith")

    def test_member_email_search(self):
        response = self.c.get("/api/v1/members/lookup/?email_address=donald")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

        response = self.c.get("/api/v1/members/lookup/?email_address=smith")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 2)
        self.assertEqual(response_objs[0]["name"], "John Smith")
        self.assertEqual(response_objs[1]["name"], "Donald Smith")

    def test_member_alt_email_search(self):
        response = self.c.get("/api/v1/members/lookup/?email_address=stripe")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

        response = self.c.get("/api/v1/members/lookup/?email_address=addl")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

    def test_member_phone_search(self):
        response = self.c.get("/api/v1/members/lookup/?phone_number=6666")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

    def test_member_combined_search(self):
        response = self.c.get("/api/v1/members/lookup/?phone_number=555&email_address=smith&name=don")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_objs = json.loads(response.content)["results"]
        self.assertEqual(len(response_objs), 1)
        self.assertEqual(response_objs[0]["name"], "Donald Smith")

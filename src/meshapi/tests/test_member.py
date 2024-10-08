import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Member
from .sample_data import sample_member


class TestMember(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def test_member(self):
        response = self.c.post(
            "/api/v1/members/",
            sample_member,
            content_type="application/json",
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_member_all_emails_field(self):
        test_member = Member(
            name="Stacy Fakename",
            primary_email_address="foo@example.com",
            additional_email_addresses=["bar@example.com", "baz@example.com"],
            stripe_email_address="stripe@example.com",
        )
        test_member.save()

        response = self.c.get(f"/api/v1/members/{test_member.id}/")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["name"], "Stacy Fakename")
        self.assertEqual(response_obj["primary_email_address"], "foo@example.com")
        self.assertEqual(response_obj["stripe_email_address"], "stripe@example.com")
        self.assertEqual(response_obj["additional_email_addresses"], ["bar@example.com", "baz@example.com"])
        self.assertEqual(
            response_obj["all_email_addresses"],
            ["foo@example.com", "stripe@example.com", "bar@example.com", "baz@example.com"],
        )

    def test_member_all_phone_numbers_field(self):
        test_member = Member(
            name="Stacy Fakename",
            primary_email_address="foo@example.com",
            phone_number="+1 212-555-5555",
            additional_phone_numbers=["+1 456-555-6666"],
        )
        test_member.save()

        response = self.c.get(f"/api/v1/members/{test_member.id}/")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["name"], "Stacy Fakename")
        self.assertEqual(response_obj["primary_email_address"], "foo@example.com")
        self.assertEqual(response_obj["phone_number"], "+1 212-555-5555")
        self.assertEqual(response_obj["additional_phone_numbers"], ["+1 456-555-6666"])
        self.assertEqual(response_obj["all_phone_numbers"], ["+1 212-555-5555", "+1 456-555-6666"])

    def test_member_phone_validation_normalization(self):
        test_member = Member(
            name="Stacy Fakename",
            primary_email_address="foo@example.com",
            phone_number="+1 212-555-5555",
            additional_phone_numbers=["+1 456-555-6666"],
        )
        test_member.save()

        # Try to make an invalid modification and ensure it causes an error
        response = self.c.patch(
            f"/api/v1/members/{test_member.id}/",
            {"phone_number": "284028"},
            content_type="application/json",
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        # Try to make an invalid modification to the additional numbers and ensure it causes an error
        response = self.c.patch(
            f"/api/v1/members/{test_member.id}/",
            {"additional_phone_numbers": ["284028"]},
            content_type="application/json",
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        # Make sure the phone number is unchanged
        test_member.refresh_from_db()
        self.assertEqual(test_member.additional_phone_numbers, ["+1 456-555-6666"])

        # Try to make a valid modification with a badly formatted number and make sure it gets normalized
        response = self.c.patch(
            f"/api/v1/members/{test_member.id}/",
            {"phone_number": "+1 212 5553333"},
            content_type="application/json",
        )
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        # Make sure the phone number is normalized
        test_member.refresh_from_db()
        self.assertEqual(test_member.phone_number, "+1 212-555-3333")

        # Try to make a valid modification with a badly formated number to the additional
        # numbers field and make sure it gets normalized
        response = self.c.patch(
            f"/api/v1/members/{test_member.id}/",
            {"additional_phone_numbers": ["+1 212 5553333"]},
            content_type="application/json",
        )
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        # Make sure the phone number is normalized
        test_member.refresh_from_db()
        self.assertEqual(test_member.additional_phone_numbers, ["+1 212-555-3333"])

    def test_broken_member(self):
        err_member = {
            "id": "Error",
            "first_name": "",
            "last_name": "",
            "primary_email_address": "",
            "phone_numer": "",
            "slack_handle": "",
        }
        response = self.c.post(
            "/api/v1/members/",
            err_member,
            content_type="application/json",
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

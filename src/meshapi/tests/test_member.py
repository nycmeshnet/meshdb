from django.contrib.auth.models import User
from django.test import Client, TestCase

from .sample_data import sample_member


class TestMember(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def test_member(self):
        response = self.c.post("/api/v1/members/", sample_member)
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_broken_member(self):
        err_member = {
            "id": "Error",
            "first_name": "",
            "last_name": "",
            "primary_email_address": "",
            "phone_numer": "",
            "slack_handle": "",
        }
        response = self.c.post("/api/v1/members/", err_member)
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

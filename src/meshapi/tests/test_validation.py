from django.test import TestCase, Client
from django.contrib.auth.models import User


class TestMember(TestCase):
    c = Client()
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def test_member(self):
        sample_member = {
            "id": "0",
            "first_name": "John",
            "last_name": "Smith",
            "email_address": "john.smith@example.com",
            "phone_numer": "555-555-5555",
            "slack_handle": "@jsmith"
        }
        response = self.c.post("/api/v1/members/", sample_member)
        assert response.status_code == 201

    def test_broken_member(self):
        sample_member = {
            "id": "Error",
            "first_name": "",
            "last_name": "",
            "email_address": "",
            "phone_numer": "",
            "slack_handle": ""
        }
        response = self.c.post("/api/v1/members/", sample_member)
        assert response.status_code == 400



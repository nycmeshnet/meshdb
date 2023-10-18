from django.test import TestCase, Client
from .sample_data import sample_member, sample_building, sample_install, sample_request


class TestJoinForm(TestCase):
    c = Client()

    def test_valid_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        join_form_submission = {
            "first_name": "John",
            "last_name": "Smith",
            "email": "jsmith@gmail.com",
            "phone": "555-555-5555",
            "street_address": "333 Chom St",
            "city": "Brooklyn",
            "state": "NY",
            "zip": 11215,
            "apartment": "3",
            "roof_access": True,
        }
        response = self.c.post("/api/v1/join/", join_form_submission, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}",
        )

    def test_empty_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        join_form_submission = {}
        response = self.c.post("/api/v1/join/", join_form_submission, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Empty Join Form. Should be {code}, but got {response.status_code}",
        )

    def test_invalid_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        join_form_submission = {
            "first_name": 25,
            "last_name": 69,
            "email": 420,
            "phone": "eight",
            "street_address": False,
            "city": True,
            "state": "NY",
            "zip": 11215,
            "apartment": 3,
            "roof_access": True,
        }
        response = self.c.post("/api/v1/join/", join_form_submission, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Invalid Join Form. Should be {code}, but got {response.status_code}",
        )

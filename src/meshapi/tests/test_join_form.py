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
            "zip": "11215",
            "apartment": "3",
            "roof_access": True,
        }
        response = self.c.post("/api/v1/join/", join_form_submission, content_type="application/json")
        self.assertEqual(response.status_code, 201, "aW jEeZ rIcHaRd")

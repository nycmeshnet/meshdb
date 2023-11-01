import json
from django.contrib.auth.models import User
from django.test import TestCase, Client
from meshapi.models import Building, Member, Install, Request
from meshapi.views import JoinFormRequest

from .sample_join_form_data import *


def validate_successful_join_form_submission(test_case, test_name, s, response):
    # Make sure that we get the right stuff out of the database afterwards

    # Check if the member was created and that we see it when we
    # filter for it.
    existing_members = Member.objects.filter(
        first_name=s.first_name,
        last_name=s.last_name,
        email_address=s.email,
        phone_number=s.phone,
    )

    length = 1
    test_case.assertEqual(
        len(existing_members),
        length,
        f"Didn't find created member for {test_name}. Should be {length}, but got {len(existing_members)}",
    )

    # Check if the building was created and that we see it when we
    # filter for it.
    existing_buildings = Building.objects.filter(
        street_address=s.street_address,
        city=s.city,
        state=s.state,
        zip_code=s.zip,
    )

    length = 1
    test_case.assertEqual(
        len(existing_buildings),
        length,
        f"Didn't find created building for {test_name}. Should be {length}, but got {len(existing_buildings)}",
    )

    # Check that a request was created
    request_id = json.loads(response.content.decode("utf-8"))["request_id"]
    join_form_requests = Request.objects.filter(pk=request_id)

    length = 1
    test_case.assertEqual(
        len(join_form_requests),
        length,
        f"Didn't find created request for {test_name}. Should be {length}, but got {len(join_form_requests)}",
    )


class TestJoinForm(TestCase):
    c = Client()
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

    def test_valid_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        response = self.c.post("/api/v1/join/", valid_join_form_submission, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        # Make sure that we get the right stuff out of the database afterwards
        s = JoinFormRequest(**valid_join_form_submission)

        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

    def test_non_nyc_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form = non_nyc_join_form_submission.copy()
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Non NYC Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        s = JoinFormRequest(**non_nyc_join_form_submission)

        validate_successful_join_form_submission(self, "Non-NYC Join Form", s, response)

    def test_empty_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        response = self.c.post("/api/v1/join/", {}, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Empty Join Form. Should be {code}, but got {response.status_code}",
        )

        # Shouldn't have any data in the database
        existing_members = Member.objects.all()
        length = 0
        self.assertEqual(
            len(existing_members),
            length,
            f"Didn't find created member for Empty Join Form. Should be {length}, but got {len(existing_members)}",
        )

        existing_buildings = Building.objects.all()

        length = 0
        self.assertEqual(
            len(existing_buildings),
            length,
            f"Search for created building for Empty Join Form was wrong. Should be {length}, but got {len(existing_buildings)}",
        )

    def test_bad_phone_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form = valid_join_form_submission.copy()
        form["phone"] = "555-555-5555"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Bad Phone Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        self.assertEqual(
            '["555-555-5555 is not a valid phone number"]', response.content.decode("utf-8"), f"Content is wrong"
        )

    def test_bad_email_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form = valid_join_form_submission.copy()
        form["email"] = "notareal@email.meshmeshmeshmeshmesh"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Bad Email Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        self.assertEqual(
            '["notareal@email.meshmeshmeshmeshmesh is not a valid email"]',
            response.content.decode("utf-8"),
            f"Content is wrong",
        )

    def test_bad_address_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form = valid_join_form_submission.copy()
        form["street_address"] = "fjdfahuweildhjweiklfhjkhklfhj"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 404
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Bad Address Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        self.assertEqual(
            '"(OSM) Address not found"',
            response.content.decode("utf-8"),
            response.content.decode("utf-8"),
        )

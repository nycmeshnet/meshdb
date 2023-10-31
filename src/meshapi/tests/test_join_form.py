from django.contrib.auth.models import User
from django.test import TestCase, Client
from meshapi.models import Building, Member, Install, Request

from .sample_join_form_data import *


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
        first_name = valid_join_form_submission.get("first_name")
        last_name = valid_join_form_submission.get("last_name")
        email_address = valid_join_form_submission.get("email")
        phone_number = valid_join_form_submission.get("phone")
        street_address = valid_join_form_submission.get("street_address")
        apartment = valid_join_form_submission.get("apartment")
        roof_access = valid_join_form_submission.get("roof_access")
        city = valid_join_form_submission.get("city")
        state = valid_join_form_submission.get("state")
        zip_code = valid_join_form_submission.get("zip")

        existing_members = Member.objects.filter(
            first_name=first_name,
            last_name=last_name,
            email_address=email_address,
            phone_number=phone_number,
        )

        length = 1
        self.assertEqual(
            len(existing_members),
            length,
            f"Didn't find created member for Valid Join Form. Should be {length}, but got {len(existing_members)}",
        )

        existing_buildings = Building.objects.filter(
            street_address=street_address,
            city=city,
            state=state,
            zip_code=zip_code,
            bin=1077609,
        )

        length = 1
        self.assertEqual(
            len(existing_buildings),
            length,
            f"Didn't find created building for Valid Join Form. Should be {length}, but got {len(existing_buildings)}",
        )

        join_form_requests = Request.objects.filter(member_id=1)

        length = 1
        self.assertEqual(
            len(join_form_requests),
            length,
            f"Didn't find created request for Valid Join Form. Should be {length}, but got {len(join_form_requests)}",
        )

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

    # FIXME: This test passing makes valid join form fail
    # Probably has something to do with hardcoding the query?
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

        # self.assertEqual(
        #    '"Address not found."',
        #    response.content.decode("utf-8"),
        #    response.content.decode("utf-8"),
        # )

    # def test_borough_join_form(self):
    #    # Name, email, phone, location, apt, rooftop, referral
    #    for form in [kings_join_form_submission, queens_join_form_submission, bronx_join_form_submission, richmond_join_form_submission]:
    #        response = self.c.post("/api/v1/join/", form, content_type="application/json")

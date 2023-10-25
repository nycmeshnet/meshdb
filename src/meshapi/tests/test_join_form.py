from django.test import TestCase, Client
from .sample_data import sample_member, sample_building, sample_install, sample_request
from meshapi.models import Building, Member, Install, Request


class TestJoinForm(TestCase):
    c = Client()

    def test_valid_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        join_form_submission = {
            "first_name": "John",
            "last_name": "Smith",
            "email": "jsmith@gmail.com",
            "phone": "+1585-758-3425",  # CSH's phone number :P
            "street_address": "151 Broome St",
            "city": "New York",
            "state": "NY",
            "zip": 10002,
            "apartment": "",
            "roof_access": True,
            "referral": "Googled it or something IDK",
        }
        response = self.c.post("/api/v1/join/", join_form_submission, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        # Make sure that we get the right stuff out of the database afterwards
        first_name = join_form_submission.get("first_name")
        last_name = join_form_submission.get("last_name")
        email_address = join_form_submission.get("email")
        phone_number = join_form_submission.get("phone")
        street_address = join_form_submission.get("street_address")
        apartment = join_form_submission.get("apartment")
        roof_access = join_form_submission.get("roof_access")
        city = join_form_submission.get("city")
        state = join_form_submission.get("state")
        zip_code = join_form_submission.get("zip")

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
        join_form_submission = {}
        response = self.c.post("/api/v1/join/", join_form_submission, content_type="application/json")

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
            f"Didn't find created building for Valid Join Form. Should be {length}, but got {len(existing_buildings)}",
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

        # Database should be empty
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
            f"Didn't find created building for Valid Join Form. Should be {length}, but got {len(existing_buildings)}",
        )

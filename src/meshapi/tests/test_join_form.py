import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from meshapi.models import Building, Install, Member
from meshapi.views import JoinFormRequest

from .sample_join_form_data import *


def validate_successful_join_form_submission(test_case, test_name, s, response):
    # Make sure that we get the right stuff out of the database afterwards

    # Check if the member was created and that we see it when we
    # filter for it.
    existing_members = Member.objects.filter(
        name=s.first_name + " " + s.last_name,
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

    # Check that a install was created
    install_number = json.loads(response.content.decode("utf-8"))["install_number"]
    join_form_installs = Install.objects.filter(pk=install_number)

    length = 1
    test_case.assertEqual(
        len(join_form_installs),
        length,
        f"Didn't find created install for {test_name}. Should be {length}, but got {len(join_form_installs)}",
    )


# Pulls the parsed_street_address out of the test data so that we don't have to later
# Returns JSON and a JoinFormRequest in the correct format to be given to the above function
def pull_apart_join_form_submission(submission):
    request = submission.copy()
    del request["parsed_street_address"]

    # Make sure that we get the right stuff out of the database afterwards
    s = JoinFormRequest(**request)

    # Match the format from OSM. I did this to see how OSM would mutate the
    # raw request we get.
    s.street_address = submission["parsed_street_address"]
    s.city = submission["city"]
    s.state = submission["state"]

    return request, s


class TestJoinForm(TestCase):
    c = Client()
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

    def test_valid_join_form(self):
        for submission in [
            valid_join_form_submission,
            richmond_join_form_submission,
            kings_join_form_submission,
            queens_join_form_submission,
            bronx_join_form_submission,
        ]:
            request, s = pull_apart_join_form_submission(submission)

            response = self.c.post("/api/v1/join/", request, content_type="application/json")
            code = 201
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
            )
            validate_successful_join_form_submission(self, "Valid Join Form", s, response)

    def test_no_ncl(self):
        request, _ = pull_apart_join_form_submission(valid_join_form_submission)

        request["ncl"] = False

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for No NCL. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    def test_non_nyc_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form, _ = pull_apart_join_form_submission(non_nyc_join_form_submission)
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Non NYC Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
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
        form, _ = pull_apart_join_form_submission(valid_join_form_submission)
        form["phone"] = "555-555-5555"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Bad Phone Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        self.assertEqual(
            '"555-555-5555 is not a valid phone number"', response.content.decode("utf-8"), f"Content is wrong"
        )

    def test_bad_email_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form, _ = pull_apart_join_form_submission(valid_join_form_submission)
        form["email"] = "notareal@email.meshmeshmeshmeshmesh"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Bad Email Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        self.assertEqual(
            '"notareal@email.meshmeshmeshmeshmesh is not a valid email"',
            response.content.decode("utf-8"),
            "Content is wrong",
        )

    def test_bad_address_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form, _ = pull_apart_join_form_submission(valid_join_form_submission)
        form["street_address"] = "fjdfahuweildhjweiklfhjkhklfhj"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Bad Address Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        self.assertEqual(
            f"\"(NYC) Address '{form['street_address']}, {form['city']}, {form['state']} {form['zip']}' not found in geosearch.planninglabs.nyc.\"",
            response.content.decode("utf-8"),
            f"Did not get correct response content for bad address join form: {response.content.decode('utf-8')}",
        )

    def test_member_moved_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(valid_join_form_submission)
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

        # Now test that the member can "move" and still access the jon form
        v_sub_2 = valid_join_form_submission.copy()
        v_sub_2["street_address"] = "152 Broome Street"

        form, s = pull_apart_join_form_submission(v_sub_2)

        # Name, email, phone, location, apt, rooftop, referral
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

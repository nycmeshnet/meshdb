import copy
import datetime
import json
import time
from unittest import mock
from unittest.mock import ANY, patch

import requests_mock
from django.contrib.auth.models import User
from django.db.models import Q
from django.test import Client, TestCase, TransactionTestCase
from flags.state import enable_flag
from parameterized import parameterized
from validate_email.exceptions import DNSTimeoutError, SMTPTemporaryError

from meshapi.models import Building, Install, Member, Node
from meshapi.views import JoinFormRequest

from ..serializers import MemberSerializer
from ..util.constants import RECAPTCHA_CHECKBOX_TOKEN_HEADER, RECAPTCHA_INVISIBLE_TOKEN_HEADER
from ..validation import BUILDING_FOOTPRINTS_API, NYC_GEOSEARCH_API, NYCAddressInfo
from .sample_data import sample_building, sample_node
from .sample_join_form_data import (
    bronx_join_form_submission,
    jefferson_join_form_submission,
    kings_join_form_submission,
    new_jersey_join_form_submission,
    non_nyc_join_form_submission,
    queens_join_form_submission,
    richmond_join_form_submission,
    valid_join_form_submission,
    valid_join_form_submission_city_needs_expansion,
    valid_join_form_submission_phone_needs_expansion,
    valid_join_form_submission_street_needs_expansion,
    valid_join_form_submission_with_apartment_in_address,
)
from .util import TestThread

# Grab a reference to the original Install.__init__ function, so that when it gets mocked
# we can still use it when we need it
original_install_init = Install.__init__


def validate_successful_join_form_submission(test_case, test_name, s, response, expected_member_count=1):
    # Make sure that we get the right stuff out of the database afterwards

    # Check if the member was created and that we see it when we
    # filter for it.
    existing_members = Member.objects.filter(
        Q(phone_number=s.phone_number)
        | Q(primary_email_address=s.email_address)
        | Q(stripe_email_address=s.email_address)
        | Q(additional_email_addresses__contains=[s.email_address])
    )

    test_case.assertEqual(
        len(existing_members),
        expected_member_count,
        f"Didn't find created member for {test_name}. Should be {expected_member_count}, but got {len(existing_members)}",
    )

    # Check if the building was created and that we see it when we
    # filter for it.
    existing_buildings = Building.objects.filter(
        street_address=s.street_address,
        city=s.city,
        state=s.state,
        zip_code=s.zip_code,
    )

    length = 1
    test_case.assertEqual(
        len(existing_buildings),
        length,
        f"Didn't find created building for {test_name}. Should be {length}, but got {len(existing_buildings)}",
    )

    # Check that a install was created
    install_number = json.loads(response.content.decode("utf-8"))["install_number"]
    join_form_installs = Install.objects.filter(install_number=install_number)

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
    del request["dob_addr_response"]
    del request["parsed_phone"]
    if "parsed_city" in request:
        del request["parsed_city"]

    # Make sure that we get the right stuff out of the database afterwards
    s = JoinFormRequest(**request)

    # Match the format from OSM. I did this to see how OSM would mutate the
    # raw request we get.
    s.street_address = submission["parsed_street_address"]
    s.city = submission["parsed_city"] if "parsed_city" in submission else submission["city"]
    s.state = submission["state"]
    s.phone_number = submission["parsed_phone"]

    return request, s


@patch("meshapi.views.forms.DISABLE_RECAPTCHA_VALIDATION", True)
class TestJoinForm(TestCase):
    c = Client()
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        self.requests_mocker = requests_mock.Mocker(real_http=True)
        self.requests_mocker.start()

        self.requests_mocker.get(BUILDING_FOOTPRINTS_API, json=[{"height_roof": 0, "ground_elevation": 0}])

    def tearDown(self):
        self.requests_mocker.stop()

    @parameterized.expand(
        [
            [valid_join_form_submission],
            [richmond_join_form_submission],
            [kings_join_form_submission],
            [queens_join_form_submission],
            [bronx_join_form_submission],
            [valid_join_form_submission_with_apartment_in_address],
        ]
    )
    def test_valid_join_form(self, submission):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=submission["dob_addr_response"],
        )

        request, s = pull_apart_join_form_submission(submission)

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )
        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

    @patch("meshapi.views.forms.validate_recaptcha_tokens")
    def test_valid_join_form_invalid_captcha(self, mock_validate_captcha_tokens):
        mock_validate_captcha_tokens.side_effect = ValueError

        with patch("meshapi.views.forms.DISABLE_RECAPTCHA_VALIDATION", False):
            self.requests_mocker.get(
                NYC_GEOSEARCH_API,
                json=valid_join_form_submission["dob_addr_response"],
            )

            request, s = pull_apart_join_form_submission(valid_join_form_submission)

            response = self.c.post(
                "/api/v1/join/",
                request,
                content_type="application/json",
                headers={
                    RECAPTCHA_INVISIBLE_TOKEN_HEADER: "",
                    RECAPTCHA_CHECKBOX_TOKEN_HEADER: "",
                },
            )
            self.assertContains(response, "Captcha verification failed", status_code=401)
            mock_validate_captcha_tokens.assert_called_once_with(None, None, None)

    @patch("meshapi.views.forms.validate_recaptcha_tokens")
    def test_valid_join_form_captcha_env_vars_not_configured(self, mock_validate_captcha_tokens):
        mock_validate_captcha_tokens.side_effect = EnvironmentError

        with patch("meshapi.views.forms.DISABLE_RECAPTCHA_VALIDATION", False):
            self.requests_mocker.get(
                NYC_GEOSEARCH_API,
                json=valid_join_form_submission["dob_addr_response"],
            )

            request, s = pull_apart_join_form_submission(valid_join_form_submission)

            response = self.c.post("/api/v1/join/", request, content_type="application/json")
            self.assertContains(response, "Captcha verification failed", status_code=401)

    @patch("meshapi.views.forms.validate_recaptcha_tokens")
    @patch("meshapi.views.forms.get_client_ip")
    def test_valid_join_form_captcha_valid(self, mock_get_client_ip, validate_captcha_tokens):
        mock_get_client_ip.return_value = ("1.1.1.1", True)
        with patch("meshapi.views.forms.DISABLE_RECAPTCHA_VALIDATION", False):
            self.requests_mocker.get(
                NYC_GEOSEARCH_API,
                json=valid_join_form_submission["dob_addr_response"],
            )

            request, s = pull_apart_join_form_submission(valid_join_form_submission)

            response = self.c.post(
                "/api/v1/join/",
                request,
                content_type="application/json",
                headers={
                    RECAPTCHA_INVISIBLE_TOKEN_HEADER: "mock_invisible_token",
                    RECAPTCHA_CHECKBOX_TOKEN_HEADER: "mock_checkbox_token",
                },
            )
            self.assertEqual(response.status_code, 201)
            validate_successful_join_form_submission(self, "Valid Join Form", s, response)
            validate_captcha_tokens.assert_called_once_with("mock_invisible_token", "mock_checkbox_token", "1.1.1.1")

    @parameterized.expand(
        [
            [valid_join_form_submission_phone_needs_expansion],
            [valid_join_form_submission_city_needs_expansion],
            [valid_join_form_submission_street_needs_expansion],
            [richmond_join_form_submission],
            [kings_join_form_submission],
            [queens_join_form_submission],
            [bronx_join_form_submission],
            [valid_join_form_submission_with_apartment_in_address],
        ]
    )
    def test_valid_join_form_with_member_confirmation(self, submission):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=submission["dob_addr_response"],
        )

        request, s = pull_apart_join_form_submission(submission)

        request["trust_me_bro"] = False

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 409
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        changed_info = response.data["changed_info"]
        if changed_info:
            for k, _ in request.items():
                if k in changed_info.keys():
                    request[k] = changed_info[k]

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )
        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

    def test_phone_number_is_silently_corrected(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=valid_join_form_submission["dob_addr_response"],
        )

        request, s = pull_apart_join_form_submission(valid_join_form_submission)

        request["phone_number"] = "+1 585-75  8-3425"
        request["trust_me_bro"] = False

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )
        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

        member = Member.objects.get(installs__install_number=response.json()["install_number"])
        self.assertEqual(member.phone_number, "+1 585-758-3425")

    def test_valid_join_form_aussie_intl_phone(self):
        request, s = pull_apart_join_form_submission(valid_join_form_submission)

        request["phone_number"] = "+61 3 96 69491 6"  # Australian bureau of meteorology (badly formatted)

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )
        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

        self.assertEqual(
            "+61 3 9669 4916",  # Australian bureau of meteorology (Aussie formatted)
            Member.objects.get(id=json.loads(response.content.decode("utf-8"))["member_id"]).phone_number,
        )

    def test_valid_join_form_guatemala_intl_phone(self):
        request, s = pull_apart_join_form_submission(valid_join_form_submission)

        request["phone_number"] = "+502 23 5 4 00 0 0"  # US Embassy in Guatemala (badly formatted)

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )
        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

        self.assertEqual(
            "+502 2354 0000",  # US Embassy in Guatemala (Properly formatted)
            Member.objects.get(id=json.loads(response.content.decode("utf-8"))["member_id"]).phone_number,
        )

    def test_valid_join_form_no_country_code_us_phone(self):
        request, s = pull_apart_join_form_submission(valid_join_form_submission)

        request["phone_number"] = "212 555 5555"

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )
        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

        self.assertEqual(
            "+1 212-555-5555",
            Member.objects.get(id=json.loads(response.content.decode("utf-8"))["member_id"]).phone_number,
        )

    def test_no_ncl(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=valid_join_form_submission["dob_addr_response"],
        )

        request, _ = pull_apart_join_form_submission(valid_join_form_submission)

        request["ncl"] = False

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for No NCL. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    def test_no_phone_or_email(self):
        request, _ = pull_apart_join_form_submission(valid_join_form_submission)

        request["email_address"] = None
        request["phone_number"] = None

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for no email & phone. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    def test_invalid_email_valid_phone(self):
        request, _ = pull_apart_join_form_submission(valid_join_form_submission)

        request["email_address"] = "aljksdafljkasfjldsaf"

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for invalid email valid phone. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    @patch("meshapi.validation.validate_email_or_fail")
    def test_email_parsing_fails(self, mock_validate):
        mock_validate.side_effect = DNSTimeoutError()
        request, _ = pull_apart_join_form_submission(valid_join_form_submission)

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 500
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for invalid email valid phone. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    @patch("meshapi.validation.validate_email_or_fail")
    def test_email_parsing_fails_temporary_issue(self, mock_validate):
        mock_validate.side_effect = SMTPTemporaryError({"err": "temporary mock issue"})
        request, _ = pull_apart_join_form_submission(valid_join_form_submission)

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for invalid email valid phone. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    @patch("meshapi.validation.validate_email_or_fail")
    def test_email_parsing_fails_temporary_issue_bad_email(self, mock_validate):
        """Check that an invalid email is given the benefit of the doubt when SMTPTemporaryError is thrown"""
        mock_validate.side_effect = SMTPTemporaryError({"err": "temporary mock issue"})
        submission = valid_join_form_submission.copy()

        submission["email_address"] = "aljksdafljkasfjldsaf"
        request, _ = pull_apart_join_form_submission(valid_join_form_submission)

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for invalid email valid phone. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    def test_non_nyc_join_form(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=non_nyc_join_form_submission["dob_addr_response"],
        )

        # Name, email, phone, location, apt, rooftop, referral
        form, _ = pull_apart_join_form_submission(non_nyc_join_form_submission)
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Non NYC Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    def test_new_jersey_join_form(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=new_jersey_join_form_submission["dob_addr_response"],
        )

        # Name, email, phone, location, apt, rooftop, referral
        form, _ = pull_apart_join_form_submission(new_jersey_join_form_submission)
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Non NYC Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    def test_new_jersey_but_nyc_zip_join_form(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=new_jersey_join_form_submission["dob_addr_response"],
        )

        # Name, email, phone, location, apt, rooftop, referral
        form, _ = pull_apart_join_form_submission(new_jersey_join_form_submission)
        form["zip_code"] = "10002"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Non NYC Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    def test_nyc_join_form_but_new_jersey_zip(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=valid_join_form_submission["dob_addr_response"],
        )

        # Name, email, phone, location, apt, rooftop, referral
        form, _ = pull_apart_join_form_submission(valid_join_form_submission)
        form["zip_code"] = "07030"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Non NYC Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

    def test_empty_join_form(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json={},
        )

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
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=valid_join_form_submission["dob_addr_response"],
        )

        # Name, email, phone, location, apt, rooftop, referral
        form, _ = pull_apart_join_form_submission(valid_join_form_submission)
        form["phone_number"] = "555-555-55555"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Bad Phone Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        con = json.loads(response.content.decode("utf-8"))

        self.assertEqual("555-555-55555 is not a valid phone number", con["detail"], "Content is wrong")

    def test_bad_email_join_form(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=valid_join_form_submission["dob_addr_response"],
        )

        # Name, email, phone, location, apt, rooftop, referral
        form, _ = pull_apart_join_form_submission(valid_join_form_submission)
        form["email_address"] = "notareal@email.meshmeshmeshmeshmesh"
        response = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Bad Email Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        con = json.loads(response.content.decode("utf-8"))

        self.assertEqual(
            "notareal@email.meshmeshmeshmeshmesh is not a valid email",
            con["detail"],
            "Content is wrong",
        )

    def test_bad_address_join_form(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json={"features": []},
        )

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

        con = json.loads(response.content.decode("utf-8"))

        self.assertEqual(
            f"Your address is invalid. Please double-check your address or contact support@nycmesh.net for assistance.",
            con["detail"],
            f"Did not get correct response content for bad address join form: {response.content.decode('utf-8')}",
        )

    def test_member_moved_join_form(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=valid_join_form_submission["dob_addr_response"],
        )

        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(valid_join_form_submission)
        response1 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response1)

        # Now test that the member can "move" and still access the join form
        v_sub_2 = valid_join_form_submission.copy()
        v_sub_2["street_address"] = "152 Broome Street"
        v_sub_2["dob_addr_response"] = copy.deepcopy(valid_join_form_submission["dob_addr_response"])
        v_sub_2["dob_addr_response"]["features"][0]["properties"]["housenumber"] = "152"

        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=v_sub_2["dob_addr_response"],
        )

        form, s = pull_apart_join_form_submission(v_sub_2)

        # Name, email, phone, location, apt, rooftop, referral
        response2 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response2.status_code}.\n Response is: {response2.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response2)

        self.assertEqual(
            json.loads(
                response1.content.decode("utf-8"),
            )["member_id"],
            json.loads(
                response2.content.decode("utf-8"),
            )["member_id"],
        )

    @mock.patch("meshapi.views.forms.notify_administrators_of_data_issue")
    def test_member_moved_join_form_but_somehow_duplicate_objects_already_exist_for_them(self, mock_admin_notif_func):
        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(valid_join_form_submission)
        response1 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response1)

        pre_existing_duplicate_member = Member(
            name="John Smith",
            primary_email_address="jsmith@gmail.com",
            phone_number="+1-555-555-5555",
        )
        pre_existing_duplicate_member.save()

        # Now test that the member can "move" and still access the join form
        v_sub_2 = valid_join_form_submission.copy()
        v_sub_2["street_address"] = "152 Broome Street"
        form, s = pull_apart_join_form_submission(v_sub_2)

        # Name, email, phone, location, apt, rooftop, referral
        response2 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response2.status_code}.\n Response is: {response2.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(
            self,
            "Valid Join Form",
            s,
            response2,
            expected_member_count=2,
        )

        mock_admin_notif_func.assert_called_once()

        self.assertEqual(
            set(mock_admin_notif_func.call_args.args[0]),
            {
                pre_existing_duplicate_member,
                Member.objects.get(
                    id=json.loads(
                        response1.content.decode("utf-8"),
                    )["member_id"]
                ),
                Member.objects.get(
                    id=json.loads(
                        response2.content.decode("utf-8"),
                    )["member_id"]
                ),
            },
        )
        self.assertEqual(mock_admin_notif_func.call_args.args[1], MemberSerializer)
        self.assertEqual(mock_admin_notif_func.call_args.args[2], "Possible duplicate member objects detected")
        self.assertIsNotNone(mock_admin_notif_func.call_args.args[3])

    @mock.patch("meshapi.views.forms.notify_administrators_of_data_issue")
    def test_member_moved_and_changed_names_join_form(self, mock_admin_notif_func):
        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(valid_join_form_submission)
        response1 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response1)

        # Now test that the member can "move", change their name and still access the join form
        v_sub_2 = valid_join_form_submission.copy()
        v_sub_2["first_name"] = "Jane"
        v_sub_2["last_name"] = "Smith"
        v_sub_2["street_address"] = "152 Broome Street"

        form, s = pull_apart_join_form_submission(v_sub_2)

        # Name, email, phone, location, apt, rooftop, referral
        response2 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response2.status_code}.\n Response is: {response2.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response2)

        # Make sure it uses the same member ID
        self.assertEqual(
            json.loads(
                response1.content.decode("utf-8"),
            )["member_id"],
            json.loads(
                response2.content.decode("utf-8"),
            )["member_id"],
        )

        # Make sure the member's name wasn't changed (prevents join form griefing)
        # but also confirm we noted the name change request, and that we sent a notification
        # to slack
        member = Member.objects.get(
            id=json.loads(
                response1.content.decode("utf-8"),
            )["member_id"]
        )
        self.assertEqual(member.name, "John Smith")
        self.assertIn("Dropped name change: Jane Smith", member.notes)

        second_install_number = json.loads(response2.content.decode("utf-8"))["install_number"]
        mock_admin_notif_func.assert_called_once_with(
            [member],
            MemberSerializer,
            f"Dropped name change: Jane Smith (install request #{second_install_number})",
            ANY,
        )

    @mock.patch("meshapi.views.forms.notify_administrators_of_data_issue")
    def test_member_moved_and_changed_names_case_only_join_form(self, mock_admin_notif_func):
        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(valid_join_form_submission)
        response1 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response1)

        # Now test that the member can "move" and still access the join form
        v_sub_2 = valid_join_form_submission.copy()
        v_sub_2["first_name"] = "john"  # Lowercase from original
        v_sub_2["last_name"] = "Smith"
        v_sub_2["street_address"] = "152 Broome Street"

        form, s = pull_apart_join_form_submission(v_sub_2)

        # Name, email, phone, location, apt, rooftop, referral
        response2 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response2.status_code}.\n Response is: {response2.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response2)

        # Make sure it uses the same member ID
        self.assertEqual(
            json.loads(
                response1.content.decode("utf-8"),
            )["member_id"],
            json.loads(
                response2.content.decode("utf-8"),
            )["member_id"],
        )

        # Make sure the member's name wasn't changed (prevents join form griefing)
        # but also confirm we noted the name change request, and that we sent a notification
        # to slack
        member = Member.objects.get(
            id=json.loads(
                response1.content.decode("utf-8"),
            )["member_id"]
        )
        self.assertEqual(member.name, "John Smith")
        self.assertEqual(None, member.notes)

        mock_admin_notif_func.assert_not_called()

    def test_member_moved_and_used_additional_email_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(valid_join_form_submission)
        response1 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response1)

        # Add the email we're going to use below (jsmith1234@yahoo.com) as an additional email
        # to confirm that we don't de-duplicate on these additional addresses
        join_form_1_member = Member.objects.get(
            id=json.loads(
                response1.content.decode("utf-8"),
            )["member_id"]
        )
        join_form_1_member.additional_email_addresses.append("jsmith1234@yahoo.com")
        join_form_1_member.save()

        # Now test that the member can "move" and still access the join form, getting a new install
        # number and member object when this happens
        v_sub_2 = valid_join_form_submission.copy()
        v_sub_2["email_address"] = "jsmith1234@yahoo.com"
        v_sub_2["street_address"] = "152 Broome Street"

        form, s = pull_apart_join_form_submission(v_sub_2)

        # Name, email, phone, location, apt, rooftop, referral
        response2 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response2.status_code}.\n Response is: {response2.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response2, expected_member_count=2)

        # Ensure we created a new member ID for the second request, since the primary email address
        # doesn't match
        self.assertNotEqual(
            json.loads(
                response1.content.decode("utf-8"),
            )["member_id"],
            json.loads(
                response2.content.decode("utf-8"),
            )["member_id"],
        )

        # Also ensure the original member's primary email wasn't changed (prevents join form griefing)
        member = Member.objects.get(
            id=json.loads(
                response1.content.decode("utf-8"),
            )["member_id"]
        )
        self.assertEqual(member.primary_email_address, "jsmith@gmail.com")

    def test_member_moved_and_used_a_new_phone_number_join_form(self):
        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(valid_join_form_submission)
        response1 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response1)

        # Now test that the member can "move" and still access the join form
        # (even with a new phone number, so long as they use the same email)
        v_sub_2 = valid_join_form_submission.copy()
        v_sub_2["phone_number"] = "+1 212-555-5555"
        v_sub_2["street_address"] = "152 Broome Street"

        form, s = pull_apart_join_form_submission(v_sub_2)

        # Name, email, phone, location, apt, rooftop, referral
        response2 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response2.status_code}.\n Response is: {response2.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response2)

        self.assertEqual(
            json.loads(
                response1.content.decode("utf-8"),
            )["member_id"],
            json.loads(
                response2.content.decode("utf-8"),
            )["member_id"],
        )

        # Make sure the member's primary phone number wasn't changed (prevents join form griefing)
        # but also confirm we noted the new phone number in additional phone numbers
        member = Member.objects.get(
            id=json.loads(
                response1.content.decode("utf-8"),
            )["member_id"]
        )
        self.assertEqual(member.phone_number, "+1 585-758-3425")
        self.assertEqual(member.additional_phone_numbers, ["+1 212-555-5555"])

    def test_member_filled_out_the_join_twice(self):
        # If someone submits the join form with identical information, there's no need to create
        # duplicate Install object
        submission = valid_join_form_submission.copy()
        submission["apartment"] = "22"

        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=submission["dob_addr_response"],
        )

        request, s = pull_apart_join_form_submission(submission)

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )
        validate_successful_join_form_submission(self, "Member filled out long ago", s, response)

        response2 = self.c.post("/api/v1/join/", request, content_type="application/json")
        self.assertEqual(
            200,
            response2.status_code,
        )
        validate_successful_join_form_submission(self, "Member filled out long ago", s, response2)

        self.assertEqual(1, Building.objects.count())
        self.assertEqual(1, Member.objects.count())
        self.assertEqual(1, Install.objects.count())

    def test_member_filled_out_the_join_form_long_ago_and_we_recycled_their_install_number(self):
        building = Building(
            street_address="151 Broome Street",
            city="New York",
            state="NY",
            zip_code="10002",
            bin=1077609,
            latitude=0,
            longitude=0,
            address_truth_sources=[],
        )
        building.save()

        member = Member(
            name="John Smith",
            primary_email_address="jsmith@gmail.com",
            phone_number="+1 585-758-3425",
        )
        member.save()

        original_install = Install(
            request_date=datetime.datetime(2013, 1, 1, 1, 1, 1),
            building=building,
            member=member,
            status=Install.InstallStatus.NN_REASSIGNED,
            unit="22",
        )
        original_install.save()

        submission = valid_join_form_submission.copy()
        submission["apartment"] = "22"

        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=submission["dob_addr_response"],
        )

        request, s = pull_apart_join_form_submission(submission)

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )

        response_json = response.json()

        self.assertNotEqual(response_json["install_id"], str(original_install.id))
        self.assertEqual(response_json["member_id"], str(member.id))
        self.assertEqual(response_json["building_id"], str(building.id))
        self.assertEqual(response_json["member_exists"], True)

        validate_successful_join_form_submission(self, "Member filled out long ago", s, response)

    def test_no_email_join_form(self):
        no_email_submission = valid_join_form_submission.copy()
        no_email_submission["email_address"] = None

        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(no_email_submission)
        response1 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

    def test_different_street_addr_same_bin_multi_node(self):
        """
        This test case simulates a new building joining the Jefferson structure to
        make sure we handle the multi-address multi-node structures correctly
        """
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=jefferson_join_form_submission["dob_addr_response"],
        )

        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(jefferson_join_form_submission)
        response1 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response1)

        # Now test that the member can "move" and still access the join form
        v_sub_2 = jefferson_join_form_submission.copy()
        v_sub_2["street_address"] = "16 Cypress Avenue"
        v_sub_2["apartment"] = "13"
        v_sub_2["dob_addr_response"] = copy.deepcopy(jefferson_join_form_submission["dob_addr_response"])
        v_sub_2["dob_addr_response"]["features"][0]["properties"]["housenumber"] = "16"
        v_sub_2["dob_addr_response"]["features"][0]["properties"]["street"] = "Cypress Avenue"

        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=v_sub_2["dob_addr_response"],
        )

        building_id_1 = json.loads(
            response1.content.decode("utf-8"),
        )["building_id"]
        building1 = Building.objects.get(id=building_id_1)
        building1.primary_node = Node(
            status=Node.NodeStatus.ACTIVE,
            latitude=building1.latitude,
            longitude=building1.longitude,
            altitude=building1.altitude,
        )
        building1.primary_node.save()
        building1.save()

        additional_node_1_for_building = Node(
            status=Node.NodeStatus.ACTIVE,
            latitude=building1.latitude,
            longitude=building1.longitude,
            altitude=building1.altitude,
        )
        additional_node_1_for_building.save()
        building1.nodes.add(additional_node_1_for_building)

        additional_node_2_for_building = Node(
            status=Node.NodeStatus.INACTIVE,
            latitude=building1.latitude,
            longitude=building1.longitude,
            altitude=building1.altitude,
        )
        additional_node_2_for_building.save()
        building1.nodes.add(additional_node_2_for_building)

        form, s = pull_apart_join_form_submission(v_sub_2)

        # Name, email, phone, location, apt, rooftop, referral
        response2 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response2.status_code}.\n Response is: {response2.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response2)

        building_id_2 = json.loads(
            response2.content.decode("utf-8"),
        )["building_id"]

        self.assertNotEqual(building_id_1, building_id_2)

        building2 = Building.objects.get(id=building_id_2)
        self.assertEqual(building1.primary_node, building2.primary_node)
        self.assertEqual(
            set(building1.nodes.all().values_list("network_number", flat=True)),
            set(building2.nodes.all().values_list("network_number", flat=True)),
        )

    def test_member_moved_and_used_non_primary_email_join_form(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=valid_join_form_submission["dob_addr_response"],
        )

        # Name, email, phone, location, apt, rooftop, referral
        form, s = pull_apart_join_form_submission(valid_join_form_submission)
        response1 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "", s, response1)

        member_object = Member.objects.get(id=json.loads(response1.content.decode("utf-8"))["member_id"])
        member_object.stripe_email_address = "jsmith+stripe@gmail.com"
        member_object.additional_email_addresses = ["jsmith+other@gmail.com"]
        member_object.save()

        # Now test that the member can move, use the stripe email address,
        # and we will NOT connect it to their old registration
        v_sub_2 = valid_join_form_submission.copy()
        v_sub_2["email_address"] = "jsmith+stripe@gmail.com"
        v_sub_2["street_address"] = "152 Broome Street"
        v_sub_2["dob_addr_response"] = copy.deepcopy(valid_join_form_submission["dob_addr_response"])
        v_sub_2["dob_addr_response"]["features"][0]["properties"]["housenumber"] = "152"

        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=v_sub_2["dob_addr_response"],
        )

        form, s = pull_apart_join_form_submission(v_sub_2)

        # Name, email, phone, location, apt, rooftop, referral
        response2 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect. Should be {code}, "
            f"but got {response2.status_code}.\n Response is: {response2.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "", s, response2, expected_member_count=2)

        self.assertNotEqual(
            str(member_object.id),
            json.loads(
                response2.content.decode("utf-8"),
            )["member_id"],
        )

        self.assertNotEqual(
            json.loads(
                response1.content.decode("utf-8"),
            )["install_number"],
            json.loads(
                response2.content.decode("utf-8"),
            )["install_number"],
        )

        # Now test that the member can move again, use an additional email address,
        # and we will still not connect it to their old registration
        v_sub_3 = valid_join_form_submission.copy()
        v_sub_3["email_address"] = "jsmith+other@gmail.com"
        v_sub_3["street_address"] = "178 Broome Street"
        v_sub_3["dob_addr_response"] = copy.deepcopy(valid_join_form_submission["dob_addr_response"])
        v_sub_3["dob_addr_response"]["features"][0]["properties"]["housenumber"] = "178"

        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=v_sub_3["dob_addr_response"],
        )

        form, s = pull_apart_join_form_submission(v_sub_3)

        # Name, email, phone, location, apt, rooftop, referral
        response3 = self.c.post("/api/v1/join/", form, content_type="application/json")

        code = 201
        self.assertEqual(
            code,
            response3.status_code,
            f"status code incorrect. Should be {code}, "
            f"but got {response3.status_code}.\n Response is: {response3.content.decode('utf-8')}",
        )

        validate_successful_join_form_submission(self, "Valid Join Form", s, response3, expected_member_count=3)

        self.assertNotEqual(
            str(member_object.id),
            json.loads(
                response3.content.decode("utf-8"),
            )["member_id"],
        )
        self.assertNotEqual(
            json.loads(
                response1.content.decode("utf-8"),
            )["install_number"],
            json.loads(
                response3.content.decode("utf-8"),
            )["install_number"],
        )

        self.assertNotEqual(
            json.loads(
                response2.content.decode("utf-8"),
            )["member_id"],
            json.loads(
                response3.content.decode("utf-8"),
            )["member_id"],
        )
        self.assertNotEqual(
            json.loads(
                response2.content.decode("utf-8"),
            )["install_number"],
            json.loads(
                response3.content.decode("utf-8"),
            )["install_number"],
        )

    def test_pre_existing_building_and_node(self):
        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=valid_join_form_submission["dob_addr_response"],
        )

        request, s = pull_apart_join_form_submission(valid_join_form_submission)

        node = Node(**sample_node)
        node.save()

        building = Building(
            street_address="151 Broome Street",
            city="New York",
            state="NY",
            zip_code="10002",
            bin=1077609,
            latitude=0.0,
            longitude=0.0,
            altitude=0.0,
            address_truth_sources=["NYCPlanningLabs"],
            primary_node=node,
        )
        building.save()

        response = self.c.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )
        validate_successful_join_form_submission(self, "Valid Join Form", s, response)

        install_number = json.loads(response.content.decode("utf-8"))["install_number"]
        install = Install.objects.get(install_number=install_number)

        self.assertEqual(install.building.id, building.id)
        self.assertEqual(install.node.network_number, node.network_number)


@patch("meshapi.views.forms.DISABLE_RECAPTCHA_VALIDATION", True)
class TestJoinFormInstallEventHooks(TestCase):
    def setUp(self):
        self.requests_mocker = requests_mock.Mocker(real_http=True)
        self.requests_mocker.start()

        self.requests_mocker.get(BUILDING_FOOTPRINTS_API, json=[{"height_roof": 0, "ground_elevation": 0}])

    def tearDown(self):
        self.requests_mocker.stop()

    @patch(
        "meshapi.util.events.join_requests_slack_channel.SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL",
        "https://mock-slack-url",
    )
    @patch(
        "meshapi.util.events.osticket_creation.OSTICKET_API_TOKEN",
        "mock-token",
    )
    @patch(
        "meshapi.util.events.osticket_creation.OSTICKET_NEW_TICKET_ENDPOINT",
        "https://mock-osticket-url",
    )
    def test_valid_join_form(self):
        enable_flag("INTEGRATION_ENABLED_SEND_JOIN_REQUEST_SLACK_MESSAGES")
        enable_flag("INTEGRATION_ENABLED_CREATE_OSTICKET_TICKETS")

        self.requests_mocker.get(
            NYC_GEOSEARCH_API,
            json=valid_join_form_submission["dob_addr_response"],
        )
        self.requests_mocker.post(
            "https://mock-slack-url",
            json={},
        )
        self.requests_mocker.post(
            "https://mock-osticket-url",
            json={},
        )

        request, s = pull_apart_join_form_submission(valid_join_form_submission)

        response = self.client.post("/api/v1/join/", request, content_type="application/json")
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response.status_code}.\n Response is: {response.content.decode('utf-8')}",
        )
        validate_successful_join_form_submission(self, "Valid Join Form", s, response)


def slow_install_init(*args, **kwargs):
    result = original_install_init(*args, **kwargs)
    time.sleep(2)
    return result


@patch("meshapi.views.forms.DISABLE_RECAPTCHA_VALIDATION", True)
class TestJoinFormRaceCondition(TransactionTestCase):
    c = Client()
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # This isn't used by the test cases here, but because of the slightly hacky way
        # we lock the DB, there needs to be at least one Member or Building object in order
        # for locking to work correctly
        building = Building(**sample_building)
        building.save()

    @patch("meshapi.views.forms.geocode_nyc_address")
    def test_valid_join_form(self, mock_geocode_func):
        results = []

        mock_geocode_func.return_value = NYCAddressInfo("151 Broome Street", "Manhattan", "NY", "10002")

        member1_submission = valid_join_form_submission.copy()
        member1_submission["email_address"] = "member1@xyz.com"
        member1_submission["phone_number"] = "+1 212 555 5555"
        member2_submission = valid_join_form_submission.copy()
        member2_submission["email_address"] = "member2@xyz.com"
        member1_submission["phone_number"] = "+1 212 555 2222"

        def invoke_join_form(submission, results):
            # Slow down the creation of the Install object to force a race condition
            with mock.patch("meshapi.views.forms.Install.__init__", slow_install_init):
                request, s = pull_apart_join_form_submission(submission)
                response = self.c.post("/api/v1/join/", request, content_type="application/json")
                results.append(response)

        t1 = TestThread(target=invoke_join_form, args=(member1_submission, results))
        time.sleep(0.5)  # Sleep to give the first thread a head start
        t2 = TestThread(target=invoke_join_form, args=(member2_submission, results))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        response1 = results[0]
        response2 = results[1]

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response1.status_code}.\n Response is: {response1.content.decode('utf-8')}",
        )

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect for Valid Join Form. Should be {code}, but got {response2.status_code}.\n Response is: {response2.content.decode('utf-8')}",
        )

        # Make sure that duplicate buildings were not created
        assert response1.data["building_id"] == response2.data["building_id"]
        assert response1.data["member_id"] != response2.data["member_id"]
        assert response1.data["install_number"] != response2.data["install_number"]

import json
from unittest.mock import patch

import pytest
import requests_mock
from django.test import RequestFactory, TestCase
from requests import RequestException

from meshapi.models import Building, Install, Member
from meshapi.serializers import MemberSerializer
from meshapi.tests.sample_data import sample_building, sample_install, sample_member
from meshapi.util.admin_notifications import notify_administrators_of_data_issue


class TestSlackNotification(TestCase):
    def setUp(self):
        self.sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        self.sample_install_copy["building"] = self.building_1

        self.sample_member = Member(**sample_member)
        self.sample_member.save()
        self.sample_install_copy["member"] = self.sample_member

        self.install = Install(**self.sample_install_copy)
        self.install.save()

    @requests_mock.Mocker()
    @patch("meshapi.util.admin_notifications.SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL", "https://mock-slack-url")
    def test_slack_notification_for_name_change(self, requests_mocker):
        member = Member(
            name="Stacy Maidenname",
            primary_email_address="stacy@example.com",
            phone_number="+1 2125555555",
            notes="Dropped name change: Stacy Marriedname (install request #98232)",
        )
        member.save()

        self.install.member = member
        self.install.save()

        rf = RequestFactory()
        mock_join_form_request = rf.post("https://mock-meshdb-url.example/join-form/")

        requests_mocker.post("https://mock-slack-url", json={})

        notify_administrators_of_data_issue(
            [member],
            MemberSerializer,
            "Dropped name change: Stacy Marriedname (install request #98232)",
            mock_join_form_request,
        )

        request_payload = json.loads(requests_mocker.request_history[0].text)
        self.assertEqual(requests_mocker.request_history[0].url, "https://mock-slack-url/")
        self.assertEqual(
            request_payload["text"],
            "Encountered the following data issue which may require admin attention: "
            "*Dropped name change: Stacy Marriedname (install request #98232)*. When processing "
            f"the following members: <http://testserver/admin/meshapi/member/{member.id}/change/|Stacy "
            "Maidenname>. Please open the database admin UI using the provided links to correct "
            "this.\n"
            "\n"
            "The current database state of these object(s) is: \n"
            "```\n"
            "[\n"
            "  {\n"
            f'    "id": "{member.id}",\n'
            '    "all_email_addresses": [\n'
            '      "stacy@example.com"\n'
            "    ],\n"
            '    "all_phone_numbers": [\n'
            '      "+1 212-555-5555"\n'
            "    ],\n"
            '    "installs": [\n'
            "      {\n"
            f'        "id": "{self.install.id}",\n'
            f'        "install_number": {self.install.install_number}\n'
            "      }\n"
            "    ],\n"
            '    "name": "Stacy Maidenname",\n'
            '    "primary_email_address": "stacy@example.com",\n'
            '    "stripe_email_address": null,\n'
            '    "additional_email_addresses": [],\n'
            '    "phone_number": "+1 212-555-5555",\n'
            '    "additional_phone_numbers": [],\n'
            '    "slack_handle": null,\n'
            '    "notes": "Dropped name change: Stacy Marriedname (install request #98232)"\n'
            "  }\n"
            "]\n"
            "```",
        )

    @requests_mock.Mocker()
    @patch("meshapi.util.admin_notifications.SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL", "https://mock-slack-url")
    def test_slack_notification_for_duplicate_members(self, requests_mocker):
        member1 = Member(
            name="Stacy Fakename",
            primary_email_address="stacy1@example.com",
            phone_number="+1 2125555555",
        )
        member1.save()

        member2 = Member(
            name="Stacy Fakename",
            primary_email_address="stacy1@example.com",
            phone_number="+1 2125553333",
        )
        member2.save()

        rf = RequestFactory()
        mock_join_form_request = rf.post("/join-form/")

        requests_mocker.post("https://mock-slack-url", json={})

        notify_administrators_of_data_issue(
            [member1, member2],
            MemberSerializer,
            "Possible duplicate member objects detected",
            mock_join_form_request,
        )

        request_payload = json.loads(requests_mocker.request_history[0].text)
        self.assertEqual(requests_mocker.request_history[0].url, "https://mock-slack-url/")
        self.assertEqual(
            request_payload["text"],
            "Encountered the following data issue which may require admin attention: "
            "*Possible duplicate member objects detected*. When processing the following members: "
            f"<http://testserver/admin/meshapi/member/{member1.id}/change/|Stacy Fakename>, "
            f"<http://testserver/admin/meshapi/member/{member2.id}/change/|Stacy Fakename>. "
            "Please open the database admin UI using the provided links to correct this.\n"
            "\n"
            "The current database state of these object(s) is: \n"
            "```\n"
            "[\n"
            "  {\n"
            f'    "id": "{member1.id}",\n'
            '    "all_email_addresses": [\n'
            '      "stacy1@example.com"\n'
            "    ],\n"
            '    "all_phone_numbers": [\n'
            '      "+1 212-555-5555"\n'
            "    ],\n"
            '    "installs": [],\n'
            '    "name": "Stacy Fakename",\n'
            '    "primary_email_address": "stacy1@example.com",\n'
            '    "stripe_email_address": null,\n'
            '    "additional_email_addresses": [],\n'
            '    "phone_number": "+1 212-555-5555",\n'
            '    "additional_phone_numbers": [],\n'
            '    "slack_handle": null,\n'
            '    "notes": null\n'
            "  },\n"
            "  {\n"
            f'    "id": "{member2.id}",\n'
            '    "all_email_addresses": [\n'
            '      "stacy1@example.com"\n'
            "    ],\n"
            '    "all_phone_numbers": [\n'
            '      "+1 212-555-3333"\n'
            "    ],\n"
            '    "installs": [],\n'
            '    "name": "Stacy Fakename",\n'
            '    "primary_email_address": "stacy1@example.com",\n'
            '    "stripe_email_address": null,\n'
            '    "additional_email_addresses": [],\n'
            '    "phone_number": "+1 212-555-3333",\n'
            '    "additional_phone_numbers": [],\n'
            '    "slack_handle": null,\n'
            '    "notes": null\n'
            "  }\n"
            "]\n"
            "```",
        )

    @requests_mock.Mocker()
    @patch("meshapi.util.admin_notifications.SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL", None)
    def test_slack_notification_for_name_change_no_env_var(self, requests_mocker):
        member = Member(
            name="Stacy Maidenname",
            primary_email_address="stacy@example.com",
            phone_number="+1 2125555555",
            notes="Dropped name change: Stacy Marriedname (install request #98232)",
        )
        member.save()

        rf = RequestFactory()
        mock_join_form_request = rf.post("https://mock-meshdb-url.example/join-form/")

        notify_administrators_of_data_issue(
            [member],
            MemberSerializer,
            "Dropped name change: Stacy Marriedname (install request #98232)",
            mock_join_form_request,
        )

        self.assertEqual(len(requests_mocker.request_history), 0)

    @requests_mock.Mocker()
    @patch("meshapi.util.admin_notifications.SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL", "https://mock-slack-url")
    def test_slack_notification_for_name_change_slack_failure(self, requests_mocker):
        member = Member(
            name="Stacy Maidenname",
            primary_email_address="stacy@example.com",
            phone_number="+1 2125555555",
            notes="Dropped name change: Stacy Marriedname (install request #98232)",
        )
        member.save()

        rf = RequestFactory()
        mock_join_form_request = rf.post("https://mock-meshdb-url.example/join-form/")

        requests_mocker.post("https://mock-slack-url", status_code=401)

        with pytest.raises(RequestException):
            notify_administrators_of_data_issue(
                [member],
                MemberSerializer,
                "Dropped name change: Stacy Marriedname (install request #98232)",
                mock_join_form_request,
                raise_exception_on_failure=True,
            )

        self.assertEqual(requests_mocker.request_history[0].url, "https://mock-slack-url/")

    @requests_mock.Mocker()
    @patch("meshapi.util.admin_notifications.SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL", "https://mock-slack-url")
    @patch("meshapi.util.admin_notifications.SITE_BASE_URL", None)
    def test_slack_notification_no_request_no_env_variable(self, requests_mocker):
        member = Member(
            name="Stacy Maidenname",
            primary_email_address="stacy@example.com",
            phone_number="+1 2125555555",
            notes="Dropped name change: Stacy Marriedname (install request #98232)",
        )
        member.save()

        requests_mocker.post("https://mock-slack-url", json={})

        notify_administrators_of_data_issue(
            [member],
            MemberSerializer,
            "Dropped name change: Stacy Marriedname (install request #98232)",
        )

        self.assertEqual(len(requests_mocker.request_history), 0)

    @requests_mock.Mocker()
    @patch("meshapi.util.admin_notifications.SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL", "https://mock-slack-url")
    @patch("meshapi.util.admin_notifications.SITE_BASE_URL", "https://mock-meshdb-url.example")
    def test_slack_notification_no_request_env_variable_fallback(self, requests_mocker):
        member = Member(
            name="Stacy Maidenname",
            primary_email_address="stacy@example.com",
            phone_number="+1 2125555555",
            notes="Dropped name change: Stacy Marriedname (install request #98232)",
        )
        member.save()

        requests_mocker.post("https://mock-slack-url", json={})

        notify_administrators_of_data_issue(
            [member],
            MemberSerializer,
            "Dropped name change: Stacy Marriedname (install request #98232)",
        )

        self.assertEqual(requests_mocker.request_history[0].url, "https://mock-slack-url/")

        request_payload = json.loads(requests_mocker.request_history[0].text)
        self.assertIn(
            "https://mock-meshdb-url.example",
            request_payload["text"],
        )

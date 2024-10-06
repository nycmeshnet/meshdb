import json
from unittest.mock import patch

import requests_mock
from django.test import TestCase
from flags.state import disable_flag, enable_flag

from meshapi.models import Building, Install, Member
from meshapi.tests.sample_data import sample_building, sample_install, sample_member


class TestInstallCreateSignals(TestCase):
    def setUp(self):
        self.sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        self.sample_install_copy["building"] = self.building_1

        self.member = Member(**sample_member)
        self.member.save()
        self.sample_install_copy["member"] = self.member

        self.maxDiff = None

    @requests_mock.Mocker()
    def test_no_events_happen_by_default(self, request_mocker):
        install = Install(**self.sample_install_copy)
        install.save()

        self.assertEqual(len(request_mocker.request_history), 0)

    @patch(
        "meshapi.util.events.join_requests_slack_channel.SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL",
        "http://example.com/test-url",
    )
    @requests_mock.Mocker()
    def test_constructing_install_triggers_slack_message(self, request_mocker):
        request_mocker.post("http://example.com/test-url", text="data")

        enable_flag("INTEGRATION_ENABLED_SEND_JOIN_REQUEST_SLACK_MESSAGES")
        disable_flag("INTEGRATION_ENABLED_CREATE_OSTICKET_TICKETS")
        install = Install(**self.sample_install_copy)
        install.save()

        self.assertEqual(len(request_mocker.request_history), 1)
        self.assertEqual(
            request_mocker.request_history[0].url,
            "http://example.com/test-url",
        )
        self.assertEqual(
            json.loads(request_mocker.request_history[0].text),
            {
                "text": f"*<https://www.nycmesh.net/map/nodes/{install.install_number}"
                f"|3333 Chom St, Brooklyn NY, 11111>*\n"
                f"Altitude not found · Roof access · No LoS Data Available"
            },
        )

    @patch(
        "meshapi.util.events.osticket_creation.OSTICKET_NEW_TICKET_ENDPOINT",
        "http://example.com/test-url",
    )
    @patch(
        "meshapi.util.events.osticket_creation.OSTICKET_API_TOKEN",
        "mock-token",
    )
    @requests_mock.Mocker()
    def test_constructing_install_triggers_osticket(self, request_mocker):
        request_mocker.post("http://example.com/test-url", text="00123456", status_code=201)

        disable_flag("INTEGRATION_ENABLED_SEND_JOIN_REQUEST_SLACK_MESSAGES")
        enable_flag("INTEGRATION_ENABLED_CREATE_OSTICKET_TICKETS")

        install = Install(**self.sample_install_copy)
        install.save()

        self.assertEqual(len(request_mocker.request_history), 1)
        self.assertEqual(
            request_mocker.request_history[0].url,
            "http://example.com/test-url",
        )
        self.assertEqual(
            json.loads(request_mocker.request_history[0].text),
            {
                "node": install.install_number,
                "userNode": install.install_number,
                "email": "john.smith@example.com",
                "name": "John Smith",
                "subject": f"NYC Mesh {install.install_number} Rooftop Install",
                "message": f"date: 2022-02-27\r\nnode: {install.install_number}\r\nname: John Smith\r\nemail: john.smith@example.com\r\nphone: +1 555-555-5555\r\nlocation: 3333 Chom St, Brooklyn NY, 11111\r\nrooftop: Rooftop install\r\nagree to ncl: True",
                "phone": "+1 555-555-5555",
                "location": "3333 Chom St, Brooklyn NY, 11111",
                "rooftop": "Rooftop install",
                "ncl": True,
                "ip": "*.*.*.*",
                "locale": "en",
            },
        )

        install.refresh_from_db()
        self.assertEqual(install.ticket_number, "00123456")

    @patch(
        "meshapi.util.events.join_requests_slack_channel.SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL",
        "",
    )
    @patch(
        "meshapi.util.events.osticket_creation.OSTICKET_NEW_TICKET_ENDPOINT",
        "",
    )
    @requests_mock.Mocker()
    def test_no_events_when_env_variables_unset(self, request_mocker):
        enable_flag("INTEGRATION_ENABLED_SEND_JOIN_REQUEST_SLACK_MESSAGES")
        enable_flag("INTEGRATION_ENABLED_CREATE_OSTICKET_TICKETS")

        install = Install(**self.sample_install_copy)
        install.save()

        self.assertEqual(len(request_mocker.request_history), 0)

    @patch(
        "meshapi.util.events.osticket_creation.OSTICKET_NEW_TICKET_ENDPOINT",
        "http://example.com/test-url",
    )
    @patch(
        "meshapi.util.events.osticket_creation.OSTICKET_API_TOKEN",
        "",
    )
    @requests_mock.Mocker()
    def test_no_osticket_event_when_no_api_token(self, request_mocker):
        enable_flag("INTEGRATION_ENABLED_CREATE_OSTICKET_TICKETS")

        install = Install(**self.sample_install_copy)
        install.save()

        self.assertEqual(len(request_mocker.request_history), 0)

    @patch(
        "meshapi.util.events.join_requests_slack_channel.SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL",
        "http://example.com/test-url",
    )
    @patch(
        "meshapi.util.events.osticket_creation.OSTICKET_NEW_TICKET_ENDPOINT",
        "http://example.com/test-url",
    )
    @patch(
        "meshapi.util.events.osticket_creation.OSTICKET_API_TOKEN",
        "mock-token",
    )
    @requests_mock.Mocker()
    def test_no_events_for_install_edit(self, request_mocker):
        install = Install(**self.sample_install_copy)
        install.save()

        enable_flag("INTEGRATION_ENABLED_SEND_JOIN_REQUEST_SLACK_MESSAGES")
        enable_flag("INTEGRATION_ENABLED_CREATE_OSTICKET_TICKETS")

        install.notes = "foo"
        install.save()

        self.assertEqual(len(request_mocker.request_history), 0)

import json
import uuid
from unittest.mock import patch

import pytest
import requests_mock
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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
                "message": "date: 2022-02-27\r\nnode: 1\r\nname: John Smith\r\nemail: john.smith@example.com\r\nphone: +1 555-555-5555\r\nlocation: 3333 Chom St, Brooklyn NY, 11111\r\nrooftop: Rooftop install\r\nagree to ncl: True",
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

    #
    # def test_constructing_install_triggers_osticket_call(self):
    #     enable_flag("INTEGRATION_ENABLED_SEND_JOIN_REQUEST_SLACK_MESSAGES")
    #     install = Install(**self.sample_install_copy)
    #     install.save()

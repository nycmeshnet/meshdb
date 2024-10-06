import logging
import os
import time

import requests
from django.db.models.base import ModelBase
from django.db.models.signals import post_save
from django.dispatch import receiver

from meshapi.models import Install
from meshapi.util.django_flag_decorator import skip_if_flag_disabled

SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL = os.environ.get("SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL")


@receiver(post_save, sender=Install, dispatch_uid="join_requests_slack_channel")
@skip_if_flag_disabled("INTEGRATION_ENABLED_SEND_JOIN_REQUEST_SLACK_MESSAGES")
def send_join_request_slack_message(sender: ModelBase, instance: Install, created: bool, **kwargs: dict) -> None:
    if not created:
        return

    install: Install = instance
    if not SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL:
        logging.error(
            f"Unable to send join request notification for install {str(install)}, did you set the "
            f"SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL environment variable?"
        )
        return

    building_height = str(int(install.building.altitude)) + "m" if install.building.altitude else "Altitude not found"
    roof_access = "Roof access" if install.roof_access else "No roof access"

    attempts = 0
    while attempts < 4:
        attempts += 1
        response = requests.post(
            SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL,
            json={
                "text": f"*<https://www.nycmesh.net/map/nodes/{install.install_number}"
                f"|{install.building.one_line_complete_address}>*\n"
                f"{building_height} · {roof_access} · No LoS Data Available"
            },
        )

        if response.status_code == 200:
            break

        time.sleep(1)

    if response.status_code != 200:
        logging.error(
            f"Got HTTP {response.status_code} while sending install create notification to "
            f"join-requests channel. HTTP response was {response.text}"
        )

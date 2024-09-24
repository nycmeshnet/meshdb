import logging
import os
from gettext import install

import requests
from django.db.models.base import ModelBase
from django.db.models.signals import post_save
from django.dispatch import receiver

from meshapi.models import Install

SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL = os.environ.get("SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL")


@receiver(post_save, sender=Install, dispatch_uid="join_requests_slack_channel")
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

    response = requests.post(
        SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL,
        json={
            "text": f"*<https://www.nycmesh.net/map/nodes/{install.install_number})"
            f"|{install.one_line_complete_address}>*\n"
            f"{building_height} · {roof_access} · No LoS Data Available"
        },
    )

    if response.status_code != 200:
        logging.error(
            f"Got HTTP {response.status_code} while sending install create notification to "
            f"join-requests channel. HTTP response was {response.text}"
        )

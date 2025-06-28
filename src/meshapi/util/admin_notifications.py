import json
import logging
import os
from typing import Optional, Sequence, Type

import requests
from django.db.models import Model
from django.http import HttpRequest
from rest_framework.serializers import Serializer

from meshapi.admin.utils import get_admin_url

SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL = os.environ.get("SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL")
SITE_BASE_URL = os.environ.get("SITE_BASE_URL")


def escape_slack_text(text: str) -> str:
    return text.replace("↔", "<->").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def notify_administrators_of_data_issue(
    model_instances: Sequence[Model],
    serializer_class: Type[Serializer],
    message: str,
    request: Optional[HttpRequest] = None,
    raise_exception_on_failure: bool = False,
) -> None:
    serializer = serializer_class(model_instances, many=True)

    site_base_url = SITE_BASE_URL
    if request:
        site_base_url = f"{request.scheme}://{request.get_host()}"

    if not site_base_url:
        logging.error(
            "Env var SITE_BASE_URL is not set and a request was not available to infer this value from, "
            "please set this variable to prevent silenced slack notifications"
        )
        return

    if "\n" not in message:
        message = f"*{message}*. "

    urls = ", ".join(f"<{get_admin_url(m, site_base_url)}|{escape_slack_text(str(m))}>" for m in model_instances)

    templated_message = (
        f"Encountered the following data issue which may require admin attention: {escape_slack_text(message)}"
        f"\n\nWhen processing the following {model_instances[0]._meta.verbose_name_plural}: "
        f"{urls}"
        ". Please open the database admin UI using the provided links to correct this.\n\n"
        "The current database state of these object(s) is: \n"
        f"```\n{json.dumps(serializer.data, indent=2, default=str)}\n```"
    )

    notify_admins(templated_message, raise_exception_on_failure)


def notify_admins(
    message: str,
    raise_exception_on_failure: bool = False,
) -> None:
    slack_message = {"text": message}

    if not SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL:
        logging.error(
            "Env var SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL is not set, please set this "
            "variable to prevent silenced notifications. Unable to notify admins of "
            f"the following message: {slack_message}"
        )
        return

    response = requests.post(SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL, json=slack_message)

    if raise_exception_on_failure:
        response.raise_for_status()
    elif response.status_code != 200:
        logging.error(
            f"Got HTTP {response.status_code} while sending slack notification to slack admin. "
            f"HTTP response was {response.text}. Unable to notify admins of "
            f"the following message: {slack_message}"
        )

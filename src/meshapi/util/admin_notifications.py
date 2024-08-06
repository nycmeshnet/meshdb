import json
import logging
import os
from typing import Sequence, Type

import requests
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.http import HttpRequest
from django.urls import reverse
from rest_framework.serializers import Serializer

SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL = os.environ.get("SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL")


def get_admin_url(model: Model) -> str:
    content_type = ContentType.objects.get_for_model(model.__class__)
    return reverse("admin:%s_%s_change" % (content_type.app_label, content_type.model), args=(model.pk,))


def notify_administrators_of_data_issue(
    model_instances: Sequence[Model],
    serializer_class: Type[Serializer],
    message: str,
    request: HttpRequest,
    raise_exception_on_failure: bool = False,
) -> None:
    serializer = serializer_class(model_instances, many=True)

    slack_message = {
        "text": f"Encountered the following data issue which may require admin attention: *{message}*. "
        f"When processing the following {model_instances[0]._meta.verbose_name_plural}: "
        + ", ".join(f"<{request.build_absolute_uri(get_admin_url(m))}|{m}>" for m in model_instances)
        + ". Please open the database admin UI using the provided links to correct this.\n\n"
        + "The current database state of these objects is: \n"
        + f"```\n{json.dumps(serializer.data, indent=2)}\n```",
    }

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

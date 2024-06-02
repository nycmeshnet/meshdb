from typing import Any, Dict

import requests
from celery import Task, shared_task
from celery.exceptions import MaxRetriesExceededError

from meshapi_hooks.hooks import CelerySerializerHook

HTTP_ATTEMPT_COUNT_PER_DELIVERY_ATTEMPT = 4


@shared_task(bind=True, max_retries=HTTP_ATTEMPT_COUNT_PER_DELIVERY_ATTEMPT - 1)
def deliver_webhook_task(self: Task, hook_id: int, payload: Dict[str, Any]) -> None:
    """Deliver the payload to the hook target"""
    hook = CelerySerializerHook.objects.get(id=hook_id)
    try:
        response = requests.post(url=hook.target, data=payload, headers=hook.headers)
        if response.status_code >= 400:
            response.raise_for_status()
    except (requests.ConnectionError, requests.HTTPError) as exc:
        try:
            self.retry(countdown=2**self.request.retries)
        except MaxRetriesExceededError:
            disable_message = (
                f"we will attempt to deliver to "
                f"this hook up to "
                f"{(hook.MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE - hook.consecutive_failures)} "
                f"more times (with {HTTP_ATTEMPT_COUNT_PER_DELIVERY_ATTEMPT} HTTP retries "
                f"each attempt) before we disable it automatically"
            )
            hook.consecutive_failures += 1
            if hook.consecutive_failures > hook.MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE:
                disable_message = (
                    f"we have disabled this hook due to exceeding the limit of "
                    f"{hook.MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE} consecutive failures"
                )
                hook.enabled = False
            hook.save()

            raise RuntimeError(
                f"Max retry count exceeded for target {hook.target}, {disable_message}",
            ) from exc

    if hook.consecutive_failures != 0:
        hook.consecutive_failures = 0
        hook.save()

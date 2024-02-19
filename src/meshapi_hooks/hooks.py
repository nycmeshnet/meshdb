from django.db import models
from drf_hooks.models import AbstractHook


class CelerySerializerHook(AbstractHook):
    """
    A drf-hooks Hook model that overrides the hook firing behavior to allow retries via Celery.
    Keeps track of the number of consecutive delivery failures, and disables delivery once
    this reaches a configurable limit
    """

    MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE = 5

    enabled = models.BooleanField(
        default=True,
        help_text="Should this webhook be used? This field be automatically changed by the system "
        "when too many consecutive failures are detected at the recipient",
    )
    consecutive_failures = models.IntegerField(
        default=0,
        help_text="The number of consecutive failures detected for this endpoint. "
        "This should not be modified by administrators",
    )

    def __str__(self):
        return f'Webhook for delivery of "{self.event}" event to {self.user}'

    class Meta:
        verbose_name = "Webhook Target"
        verbose_name_plural = "Webhook Targets"

    def deliver_hook(self, serialized_hook):
        # Inline import to prevent circular import loop
        from meshapi_hooks.tasks import deliver_webhook_task

        deliver_webhook_task.apply_async([self.id, serialized_hook])

    @classmethod
    def find_hooks(cls, event_name, user=None):
        hooks = super().find_hooks(event_name, user=user)
        return hooks.filter(enabled=True)

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.module_loading import import_string
from drf_hooks.models import AbstractHook, get_event_lookup

from meshapi.serializers import RecursiveSerializer


class MockRequestForWebhookSerializer:
    """
    An object which defines a .user attribute that we can pass to our serializers in place of an
    actual DRF Request object. These are complex to construct, and since we only need to access
    the user attribute inside the serializer, this mock performs just fine.
    """

    def __init__(self, user: User):
        self.user = user

    def __getattribute__(self, item):
        if item == "user":
            return super().__getattribute__(item)
        else:
            raise AttributeError(
                f"MockRequestForWebhookSerializer does not define {item}. Perhaps you need to add it in hooks.py?"
            )


class RecursiveSerializerHook(AbstractHook):
    """
    A drf-hooks Hook model that overrides the hook firing behavior to allow the use of our
    RecursiveSerializer. The biggest issues with the built-in serializer are 1) that our serializer
     must be called separately per hook (since the user could change between hooks) and 2) that
     the user needs to be made available to the Serializer in the first place, via the request object
     that the default Hook does not set
    """

    @classmethod
    def handle_model_event(cls, instance, action):
        events = get_event_lookup()
        model = instance._meta.label
        if model not in events or action not in events[model]:
            return
        event_name, all_users = events[model][action]
        assert all_users, (
            "RecursiveSerializerHook requires all user permissions, "
            "did you forget a + in HOOK_EVENTS in settings.py?"
        )
        cls.find_and_fire_hooks_for_instance(event_name, instance)

    def serialize_model_for_user(self, instance, user):
        hook_srls = getattr(settings, "HOOK_SERIALIZERS", {})
        if instance._meta.label in hook_srls:
            serializer = import_string(hook_srls[instance._meta.label])
            if not issubclass(serializer, RecursiveSerializer):
                raise ValueError(
                    f"Serializer {hook_srls[instance._meta.label]} specified in HOOK_SERIALIZERS "
                    f"is not a subclass of RecursiveSerializer, "
                    f"which is a requirement to use the RecursiveSerializerHook"
                )
            context = {"request": MockRequestForWebhookSerializer(user=user)}
            return serializer(instance, context=context).data
        else:
            raise ValueError(
                f"Could not find serializer for {instance._meta.label} in HOOK_SERIALIZERS in "
                f"settings.py, but RecursiveSerializerHook requires one! Did you forget to include"
                f"a serializer for each model specified in HOOK_EVENTS"
            )

    @classmethod
    def find_and_fire_hooks_for_instance(cls, event_name, instance):
        for hook in cls.find_hooks(event_name, None):
            serialized_hook = hook.serialize_hook(hook.serialize_model_for_user(instance, hook.user))
            hook.deliver_hook(serialized_hook)


class CeleryRecursiveSerializerHook(RecursiveSerializerHook):
    """
    A drf-hooks Hook model that overrides the hook firing behavior to allow retries via Celery.
    Keeps track of the number of consecutive delivery failures, and disables delivery once
    this reaches a configurable limit

    Happens to also inherit from RecursiveSerializerHook so that recurisve serializers are used,
    but nothing in this class prevent use with the generic AbstractHook class
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

import logging
import os
import time
from typing import List, Optional

import stripe
from django.db.models.base import ModelBase
from django.db.models.signals import post_save
from django.dispatch import receiver

from meshapi.models import Install, Node
from meshapi.serializers import InstallSerializer
from meshapi.util.admin_notifications import notify_administrators_of_data_issue
from meshapi.util.django_flag_decorator import skip_if_flag_disabled
from meshapi.util.django_pglocks import advisory_lock

STRIPE_API_TOKEN = os.environ.get("STRIPE_API_TOKEN")


def fetch_existing_installs(subscription_id: str) -> Optional[List[int]]:
    attempts = 0
    stripe_error = None
    while attempts < 4:
        attempts += 1

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return [int(install_num) for install_num in subscription.metadata.get("installs", "").split(",")]
        except stripe.error.InvalidRequestError as e:
            if e.http_status == 404:
                return None
            stripe_error = e
        except stripe.error.StripeError as e:
            stripe_error = e

        time.sleep(1)

    raise RuntimeError(f"Unable to query Stripe for subscription_id {subscription_id}") from stripe_error


def remove_install_from_subscription(install_number: int, subscription_id: str) -> None:
    logging.info(f"Removing install number {install_number} from Stripe subscription_id {subscription_id}...")
    existing_installs = fetch_existing_installs(subscription_id)

    if existing_installs is None:
        logging.warning(f"No Stripe subscription found with id {subscription_id}. Taking no action")
        return

    if install_number not in existing_installs:
        logging.info(
            f"Stripe subscription_id {subscription_id} does not have install {install_number}, taking no action"
        )
        return

    attempts = 0
    stripe_error = None
    while attempts < 4:
        attempts += 1

        try:
            stripe.Subscription.modify(
                subscription_id,
                metadata={
                    "installs": ",".join(
                        str(install) for install in sorted(existing_installs) if install != install_number
                    )
                },
            )
            return
        except stripe.error.StripeError as e:
            stripe_error = e

        time.sleep(1)

    raise RuntimeError(
        f"Unable to remove install {install_number} from Stripe subscription_id {subscription_id}"
    ) from stripe_error


def add_install_to_subscription(install_number: int, subscription_id: str):
    logging.info(f"Adding install number {install_number} to Stripe subscription_id {subscription_id}...")
    existing_installs = fetch_existing_installs(subscription_id)

    if existing_installs is None:
        logging.warning(f"No Stripe subscription found with id {subscription_id}. Taking no action")
        return

    if install_number in existing_installs:
        logging.info(f"Stripe subscription_id {subscription_id} already has install {install_number}, taking no action")
        return

    existing_installs.append(install_number)

    attempts = 0
    stripe_error = None
    while attempts < 4:
        attempts += 1

        try:
            stripe.Subscription.modify(
                subscription_id, metadata={"installs": ",".join(str(install) for install in sorted(existing_installs))}
            )
            return
        except stripe.error.StripeError as e:
            stripe_error = e

        time.sleep(1)

    raise RuntimeError(
        f"Unable to add install {install_number} to Stripe subscription_id {subscription_id}"
    ) from stripe_error


@receiver(post_save, sender=Install, dispatch_uid="update_stripe_subscription")
@skip_if_flag_disabled("INTEGRATION_ENABLED_UPDATE_STRIPE_SUBSCRIPTIONS")
@advisory_lock("update_stripe_subscription")  # TODO: Test this race condition
def update_stripe_subscription_on_install_update(
    sender: ModelBase, instance: Install, created: bool, **kwargs: dict
) -> None:
    install: Install = instance
    install.refresh_from_db()

    if not STRIPE_API_TOKEN:
        logging.error(
            f"Unable to contact Stripe for update to install {str(install)}, did you set the STRIPE_API_TOKEN env var?"
        )
        return

    stripe.api_key = STRIPE_API_TOKEN

    current_stripe_subscription_id = install.stripe_subscription_id or ""
    install_history = install.history.all()
    if len(install_history) > 1:
        former_stripe_subscription_id = install_history[1].stripe_subscription_id
    else:
        former_stripe_subscription_id = None

    logging.info(
        f"After an update to install number {install.install_number}, old stripe subscription ID is "
        f"{former_stripe_subscription_id}, new one is {current_stripe_subscription_id}"
    )

    try:
        if former_stripe_subscription_id and current_stripe_subscription_id != former_stripe_subscription_id:
            remove_install_from_subscription(install.install_number, former_stripe_subscription_id)

        if current_stripe_subscription_id and current_stripe_subscription_id != former_stripe_subscription_id:
            add_install_to_subscription(install.install_number, current_stripe_subscription_id)
    except RuntimeError:
        error_summary = (
            f"Fatal exception (after retries) when trying to update the Stripe subscription(s): "
            + f"{[former_stripe_subscription_id, current_stripe_subscription_id]}"
        )

        notify_administrators_of_data_issue([install], InstallSerializer, error_summary)
        logging.exception(f"{error_summary} during an update to install number {install.install_number}")

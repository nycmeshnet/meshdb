from unittest.mock import MagicMock, patch

import pytest
import stripe
from django.test import TestCase

from meshapi.util.events.update_stripe_subscription import (
    add_install_to_subscription,
    fetch_existing_installs,
    remove_install_from_subscription,
)


class TestStripeHelpers(TestCase):
    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_fetch_single(self, mock_stripe):
        mock_subscription = MagicMock()
        mock_subscription.metadata = {"installs": "1234"}

        mock_stripe.Subscription.retrieve.return_value = mock_subscription

        self.assertEqual(fetch_existing_installs("sub_mockid"), [1234])
        mock_stripe.Subscription.retrieve.assert_called_with("sub_mockid")

    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_fetch_many(self, mock_stripe):
        mock_subscription = MagicMock()
        mock_subscription.metadata = {"installs": "1234,567,9810"}

        mock_stripe.Subscription.retrieve.return_value = mock_subscription

        self.assertEqual(fetch_existing_installs("sub_mockid"), [1234, 567, 9810])
        mock_stripe.Subscription.retrieve.assert_called_with("sub_mockid")

    @patch("meshapi.util.events.update_stripe_subscription.stripe.Subscription")
    def test_fetch_non_existent(self, mock_stripe_Subscription):
        mock_stripe_Subscription.retrieve.side_effect = stripe.InvalidRequestError(
            "foo_message", "foo_param", http_status=404
        )

        self.assertEqual(fetch_existing_installs("sub_mockid"), None)
        mock_stripe_Subscription.retrieve.assert_called_with("sub_mockid")

    @patch("meshapi.util.events.update_stripe_subscription.stripe.Subscription")
    def test_fetch_other_invalid(self, mock_stripe_Subscription):
        mock_stripe_Subscription.retrieve.side_effect = stripe.InvalidRequestError("foo_message", "foo_param")

        with pytest.raises(RuntimeError):
            fetch_existing_installs("sub_mockid")

        mock_stripe_Subscription.retrieve.assert_called_with("sub_mockid")
        self.assertEqual(mock_stripe_Subscription.retrieve.call_count, 4)

    @patch("meshapi.util.events.update_stripe_subscription.stripe.Subscription")
    def test_fetch_other_error(self, mock_stripe_Subscription):
        mock_stripe_Subscription.retrieve.side_effect = stripe.PermissionError

        with pytest.raises(RuntimeError):
            fetch_existing_installs("sub_mockid")

        mock_stripe_Subscription.retrieve.assert_called_with("sub_mockid")
        self.assertEqual(mock_stripe_Subscription.retrieve.call_count, 4)

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_add_clean_slate(self, mock_stripe, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = []

        add_install_to_subscription(1234, "sub_mockid")
        mock_stripe.Subscription.modify.assert_called_with("sub_mockid", metadata={"installs": "1234"})

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_add_to_existing(self, mock_stripe, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = [5678]

        add_install_to_subscription(1234, "sub_mockid")
        mock_stripe.Subscription.modify.assert_called_with("sub_mockid", metadata={"installs": "1234,5678"})

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_add_dont_duplicate(self, mock_stripe, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = [1234, 5678]

        add_install_to_subscription(1234, "sub_mockid")
        mock_stripe.Subscription.modify.assert_not_called()

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_add_to_non_existent_subscription(self, mock_stripe, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = None

        add_install_to_subscription(1234, "sub_mockid")
        mock_stripe.Subscription.modify.assert_not_called()

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe.Subscription")
    def test_add_throws_exception(self, mock_stripe_Subscription, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = []

        mock_stripe_Subscription.modify.side_effect = stripe.PermissionError

        with pytest.raises(RuntimeError):
            add_install_to_subscription(1234, "sub_mockid")

        mock_stripe_Subscription.modify.assert_called_with("sub_mockid", metadata={"installs": "1234"})
        self.assertEqual(mock_stripe_Subscription.modify.call_count, 4)

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_remove_non_existing(self, mock_stripe, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = []
        remove_install_from_subscription(1234, "sub_mockid")

        mock_fetch_existing_installs.return_value = [5678]
        remove_install_from_subscription(1234, "sub_mockid")

        mock_stripe.Subscription.modify.assert_not_called()

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_remove_install(self, mock_stripe, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = [1234]

        remove_install_from_subscription(1234, "sub_mockid")
        mock_stripe.Subscription.modify.assert_called_with("sub_mockid", metadata={"installs": ""})

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_remove_only_targeted_install(self, mock_stripe, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = [1234, 5678]

        remove_install_from_subscription(1234, "sub_mockid")
        mock_stripe.Subscription.modify.assert_called_with("sub_mockid", metadata={"installs": "5678"})

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe")
    def test_remove_from_non_existent_subscription(self, mock_stripe, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = None

        remove_install_from_subscription(1234, "sub_mockid")
        mock_stripe.Subscription.modify.assert_not_called()

    @patch("meshapi.util.events.update_stripe_subscription.fetch_existing_installs")
    @patch("meshapi.util.events.update_stripe_subscription.stripe.Subscription")
    def test_remove_throws_exception(self, mock_stripe_Subscription, mock_fetch_existing_installs):
        mock_fetch_existing_installs.return_value = [1234]

        mock_stripe_Subscription.modify.side_effect = stripe.PermissionError

        with pytest.raises(RuntimeError):
            remove_install_from_subscription(1234, "sub_mockid")

        mock_stripe_Subscription.modify.assert_called_with("sub_mockid", metadata={"installs": ""})
        self.assertEqual(mock_stripe_Subscription.modify.call_count, 4)

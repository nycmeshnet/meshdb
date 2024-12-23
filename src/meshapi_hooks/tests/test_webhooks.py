import multiprocessing
import queue
from datetime import timezone

from django.contrib.auth.models import Permission, User
from django.utils.datetime_safe import datetime
from flask import Flask, Response, request

from meshapi.util.uisp_import.update_objects import update_device_from_uisp_data
from meshapi_hooks.hooks import CelerySerializerHook

multiprocessing.set_start_method("fork")

from celery.contrib.testing.worker import start_worker
from django.test import TransactionTestCase

from meshapi.models import Building, Device, Install, Member, Node
from meshapi.tests.sample_data import sample_building, sample_device, sample_install, sample_member, sample_node
from meshdb.celery import app as celery_app

HTTP_CALL_WAITING_TIME = 2  # Seconds


def dummy_webhook_listener(http_requests_queue, bad_requests_counter):
    flask_app = Flask(__name__)

    flaky_request_index = 0

    @flask_app.route("/webhook", methods=["POST"])
    def respond():
        http_requests_queue.put(request.json)
        return Response(status=200)

    @flask_app.route("/flaky-webhook", methods=["POST"])
    def respond_flaky():
        nonlocal flaky_request_index
        if flaky_request_index == 0:
            # Pretend to fail handling the first request, to make sure we do retries
            flaky_request_index += 1
            return Response(status=500)

        http_requests_queue.put(request.json)
        return Response(status=200)

    @flask_app.route("/bad-webhook", methods=["POST"])
    def respond_bad():
        with bad_requests_counter.get_lock():
            bad_requests_counter.value += 1
        return Response(status=500)

    flask_app.run(host="127.0.0.1", port=8091, debug=False)


class TestMeshAPIWebhooks(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Start the celery worker inside the test case
        cls.celery_worker = start_worker(celery_app, perform_ping_check=False, loglevel="info")
        cls.celery_worker.__enter__()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.celery_worker.__exit__(None, None, None)

    def setUp(self):
        # Pre-create some example models to use later,
        # before we activate the webhook listener
        self.member_obj = Member(**sample_member)
        self.member_obj.save()
        self.building_obj = Building(**sample_building)
        self.building_obj.save()

        # Create a simple HTTP listener using flask
        self.http_requests_queue = multiprocessing.Queue()
        self.bad_requests_counter = multiprocessing.Value("i", 0)
        self.app_process = multiprocessing.Process(
            target=dummy_webhook_listener,
            args=(self.http_requests_queue, self.bad_requests_counter),
        )
        self.app_process.start()

        self.hook_user = User.objects.create_user(
            username="hook_client_application", password="test_pw", email="client@example.com"
        )
        self.hook_user.user_permissions.add(Permission.objects.get(codename="view_member"))
        self.hook_user.user_permissions.add(Permission.objects.get(codename="view_install"))
        self.hook_user.user_permissions.add(Permission.objects.get(codename="view_device"))

        # For testing, just so that we don't have to wait around for a large number of failures
        CelerySerializerHook.MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE = 1

        # Create the webhooks in Django
        # (this would be done by an admin via the UI in prod)
        member_webhook = CelerySerializerHook(
            user=self.hook_user,
            target="http://localhost:8091/webhook",
            event="member.created",
        )
        member_webhook.save()
        install_webhook = CelerySerializerHook(
            user=self.hook_user,
            target="http://localhost:8091/webhook",
            event="install.created",
        )
        install_webhook.save()

        building_webhook = CelerySerializerHook(
            enabled=False,
            user=self.hook_user,
            target="http://localhost:8091/webhook",
            event="install.created",
        )
        building_webhook.save()

    def tearDown(self) -> None:
        self.app_process.terminate()

    def test_member(self):
        # Create new member triggers webhook
        member_obj = Member(**sample_member)
        member_obj.save()

        try:
            flask_request = self.http_requests_queue.get(timeout=HTTP_CALL_WAITING_TIME)
        except queue.Empty as e:
            raise RuntimeError("HTTP server not called...") from e

        for key, value in sample_member.items():
            assert flask_request["data"][key] == value

        # This member doesn't have a linked install
        assert flask_request["data"]["installs"] == []

        assert flask_request["hook"]["event"] == "member.created"
        assert flask_request["hook"]["target"] == "http://localhost:8091/webhook"
        assert flask_request["hook"]["id"]

    def test_flaky_hook(self):
        # Modify the member hook to use the flaky endpoint
        member_hook = CelerySerializerHook.objects.get(event="member.created")
        member_hook.target = "http://localhost:8091/flaky-webhook"
        member_hook.save()

        # Create new member triggers webhook
        member_obj = Member(**sample_member)
        member_obj.save()

        try:
            flask_request = self.http_requests_queue.get(
                timeout=HTTP_CALL_WAITING_TIME * 2,  # Wait extra time before giving up, for the retry to happen
            )
        except queue.Empty as e:
            raise RuntimeError("HTTP server not called...") from e

        for key, value in sample_member.items():
            assert flask_request["data"][key] == value

        # This member doesn't have a linked install
        assert flask_request["data"]["installs"] == []

        assert flask_request["hook"]["event"] == "member.created"
        assert flask_request["hook"]["target"] == "http://localhost:8091/flaky-webhook"
        assert flask_request["hook"]["id"]

    def test_webhook_gets_disabled_after_many_retries(self):
        # Modify the member hook to use the flaky endpoint
        member_hook = CelerySerializerHook.objects.get(event="member.created")
        member_hook.target = "http://localhost:8091/bad-webhook"
        member_hook.save()

        # Create new member triggers webhook
        member_obj = Member(**sample_member)
        member_obj.save()

        try:
            self.http_requests_queue.get(
                timeout=HTTP_CALL_WAITING_TIME * 5,  # Wait extra time before giving up, for the retries to happen
            )
            assert False, "/webhook HTTP endpoint shouldn't have been called (only /bad-webhook)"
        except queue.Empty:
            pass

        # We have failed once, check that we have recorded this failure in the hook object
        # and that the webhook was actually called multiple times
        member_hook.refresh_from_db()
        assert member_hook.consecutive_failures == 1
        assert member_hook.enabled

        with self.bad_requests_counter.get_lock():
            assert self.bad_requests_counter.value == 4

        # Create new member again to trigger another failure
        member_obj = Member(**sample_member)
        member_obj.save()

        try:
            self.http_requests_queue.get(
                timeout=HTTP_CALL_WAITING_TIME * 5,  # Wait extra time before giving up, for the retries to happen
            )
            assert False, "/webhook HTTP endpoint shouldn't have been called (only /bad-webhook)"
        except queue.Empty:
            pass

        # We have failed once, check that we have recorded this failure in the hook object
        # and that the webhook was actually called multiple times. Also for testing, we have
        # reduced the tolerable failure limit, which means this hook should now be disabled
        member_hook.refresh_from_db()
        assert member_hook.consecutive_failures == 2
        assert not member_hook.enabled

        with self.bad_requests_counter.get_lock():
            assert self.bad_requests_counter.value == 8

    def test_install(self):
        # Create new install triggers webhook
        sample_install_copy = sample_install.copy()
        sample_install_copy["building"] = self.building_obj
        sample_install_copy["member"] = self.member_obj
        install_obj = Install(**sample_install_copy)
        install_obj.save()

        try:
            flask_request = self.http_requests_queue.get(timeout=HTTP_CALL_WAITING_TIME)
        except queue.Empty as e:
            raise RuntimeError("HTTP server not called...") from e

        for key, value in sample_install_copy.items():
            if key not in ["building", "member"]:
                assert flask_request["data"][key] == value

        assert flask_request["data"]["building"]["id"] == str(self.building_obj.id)
        assert flask_request["data"]["member"]["id"] == str(self.member_obj.id)
        assert flask_request["data"]["install_number"] == install_obj.install_number
        assert flask_request["data"]["node"] is None

        assert flask_request["hook"]["event"] == "install.created"
        assert flask_request["hook"]["target"] == "http://localhost:8091/webhook"
        assert flask_request["hook"]["id"]

    def test_building(self):
        # Create new building doesn't trigger webhook (there's a webhook object, but it's disabled)
        building_obj = Building(**sample_building)
        building_obj.save()

        try:
            self.http_requests_queue.get(timeout=HTTP_CALL_WAITING_TIME)
            assert False, "HTTP server shouldn't have been called"
        except queue.Empty:
            pass

    def test_uisp_update_event(self):
        # UISP update triggers custom webhook
        device_webhook = CelerySerializerHook(
            enabled=True,
            user=self.hook_user,
            target="http://localhost:8091/webhook",
            event="device.uisp-deactivated",
        )
        device_webhook.save()

        uisp_node = Node(**sample_node)
        uisp_node.save()

        existing_device = Device(**sample_device)
        existing_device.node = uisp_node
        existing_device.save()

        uisp_name = "test"
        uisp_status = Device.DeviceStatus.INACTIVE

        uisp_last_seen = datetime(1970, 1, 1, 1, 1, 1, tzinfo=timezone.utc)

        update_device_from_uisp_data(
            existing_device,
            uisp_node,
            uisp_name,
            uisp_status,
            uisp_last_seen,
        )

        try:
            flask_request = self.http_requests_queue.get(timeout=HTTP_CALL_WAITING_TIME)
        except queue.Empty as e:
            raise RuntimeError("HTTP server not called...") from e

        assert flask_request["data"]["id"] == str(existing_device.id)
        assert flask_request["data"]["status"] == "Inactive"
        assert flask_request["data"]["abandon_date"] == "1970-01-01"
        assert flask_request["data"]["node"]["id"] == str(uisp_node.id)
        assert flask_request["data"]["node"]["network_number"] == uisp_node.network_number

        assert flask_request["hook"]["event"] == "device.uisp-deactivated"
        assert flask_request["hook"]["target"] == "http://localhost:8091/webhook"
        assert flask_request["hook"]["id"]

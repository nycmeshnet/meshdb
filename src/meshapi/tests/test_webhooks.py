import multiprocessing
import queue

from flask import Flask, Response, request

multiprocessing.set_start_method("fork")

import django_webhook.models
from celery.contrib.testing.worker import start_worker
from django.test import TransactionTestCase
from django_webhook.models import Webhook, WebhookTopic

from meshdb.celery import app as celery_app

from ..models import Building, Install, Member
from .sample_data import sample_building, sample_install, sample_member

HTTP_CALL_WAITING_TIME = 2  # Seconds


def dummy_webhook_listener(http_requests_queue):
    flask_app = Flask(__name__)

    @flask_app.route("/webhook", methods=["POST"])
    def respond():
        http_requests_queue.put(request.json)
        return Response(status=200)

    flask_app.run(host="127.0.0.1", port=8089, debug=False)


class TestMemberWebhook(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Start the celery worker inside the test case
        cls.celery_worker = start_worker(celery_app, perform_ping_check=False)
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
        self.app_process = multiprocessing.Process(
            target=dummy_webhook_listener,
            args=(self.http_requests_queue,),
        )
        self.app_process.start()

        # Load the possible webhook topics from the models, normally this happens
        # at migration time but the test DB is odd
        django_webhook.models.populate_topics_from_settings()

        # Create the webhook in Django
        # (this would be done by an admin via the UI in prod)
        webhook = Webhook(url="http://localhost:8089/webhook")
        topics = [
            WebhookTopic.objects.get(name="meshapi.Member/create"),
            WebhookTopic.objects.get(name="meshapi.Install/create"),
        ]
        webhook.save()
        webhook.topics.set(topics)
        webhook.save()

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

        assert flask_request["topic"] == "meshapi.Member/create"
        for key, value in sample_member.items():
            assert flask_request["object"][key] == value
        assert flask_request["object_type"] == "meshapi.Member"
        assert flask_request["webhook_uuid"]

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

        assert flask_request["topic"] == "meshapi.Install/create"
        for key, value in sample_install_copy.items():
            if key not in ["building", "member"]:
                assert flask_request["object"][key] == value

        assert flask_request["object"]["building"]["id"] == self.building_obj.id
        assert flask_request["object"]["building"]["bin"] == self.building_obj.bin
        assert flask_request["object"]["member"]["id"] == self.member_obj.id
        assert flask_request["object"]["member"]["email_address"] == self.member_obj.email_address

        assert flask_request["object_type"] == "meshapi.Install"
        assert flask_request["webhook_uuid"]

    def test_building(self):
        # Create new building doesn't trigger webhook (they're not subscribed)
        building_obj = Building(**sample_building)
        building_obj.save()

        try:
            self.http_requests_queue.get(timeout=HTTP_CALL_WAITING_TIME)
            assert False, "HTTP server shouldn't have been called"
        except queue.Empty:
            pass

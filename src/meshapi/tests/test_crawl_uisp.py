# @patch("meshapi.util.join_records.JOIN_RECORD_PREFIX", MOCK_JOIN_RECORD_PREFIX)
from django.contrib.auth.models import User
from django.test import Client, TestCase


class TestJoinRecordViewer(TestCase):
    a = Client()  # Anonymous client
    c = Client()

    def setUp(self) -> None:
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def test_uisp_on_demand_unauthenticated(self):
        response = self.a.get("/uisp-on-demand/")
        # Redirected to admin login
        self.assertEqual(302, response.status_code)

    def test_uisp_on_demand(self):
        response = self.c.get("/uisp-on-demand/")
        # Redirected to admin login
        self.assertEqual(302, response.status_code)

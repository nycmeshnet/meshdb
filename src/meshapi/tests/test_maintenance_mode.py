from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client
from flags.state import disable_flag, enable_flag, flag_disabled, flag_enabled


class TestMaintenanceMode(TestCase):
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

    # Very basic sanity check
    def test_maintenance_mode(self):
        response = self.client.get("/api/v1/")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect for /api/v1/. Should be 200, but got {response.status_code}",
        )
        enable_flag("MAINTENANCE_MODE")
        response = self.client.get("/api/v1/")
        self.assertEqual(
            302,
            response.status_code,
            f"status code incorrect for /api/v1/. Should be 302, but got {response.status_code}",
        )
        disable_flag("MAINTENANCE_MODE")
        response = self.client.get("/api/v1/")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect for /api/v1/. Should be 200, but got {response.status_code}",
        )

    def test_maintenance_mode_redirect(self):
        route = "/maintenance/"
        expected_code = 302
        response = self.client.get(route)
        self.assertEqual(
            response.status_code,
            expected_code,
            f"status code incorrect for {route}. Should be {expected_code}, but got {response.status_code}",
        )

    def test_maintenance_mode_routes(self):
        route = "/maintenance/enable/"
        expected_code = 403
        response = self.client.post(route)
        self.assertEqual(
            response.status_code,
            expected_code,
            f"status code incorrect for {route}. Should be {expected_code}, but got {response.status_code}",
        )

        route = "/maintenance/enable/"
        expected_code = 200
        response = self.admin_c.post(route)
        self.assertEqual(
            response.status_code,
            expected_code,
            f"status code incorrect for {route}. Should be {expected_code}, but got {response.status_code}",
        )

        self.assertTrue(flag_enabled("MAINTENANCE_MODE"))

        route = "/maintenance/disable/"
        expected_code = 403
        response = self.client.post(route)
        self.assertEqual(
            response.status_code,
            expected_code,
            f"status code incorrect for {route}. Should be {expected_code}, but got {response.status_code}",
        )

        route = "/maintenance/disable/"
        expected_code = 200
        response = self.admin_c.post(route)
        self.assertEqual(
            response.status_code,
            expected_code,
            f"status code incorrect for {route}. Should be {expected_code}, but got {response.status_code}",
        )

        self.assertTrue(flag_disabled("MAINTENANCE_MODE"))

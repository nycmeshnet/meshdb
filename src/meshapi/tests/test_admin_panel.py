from django.contrib.auth.models import User
from django.test import Client, TestCase


class TestAdminPanel(TestCase):
    c = Client()

    def setUp(self) -> None:
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    # TODO (wdn): Add more tests checking if navigating to xyz page works
    def test_iframe_loads(self):
        route = "/admin/panel/"
        code = 200
        response = self.c.get(route)
        self.assertEqual(code, response.status_code, f"Could not view {route} in the admin panel.")

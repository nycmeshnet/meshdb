from django.test import TestCase, Client
from django.contrib.auth.models import User

# Create your tests here.


class TestViewsCodesUnauthenticated(TestCase):
    c = Client()

    def test_all_views_codes_unauthenticated(self):
        routes = [
            ("/api/v1/", 200),
            ("/api/v1", 301),
            ("/api/v1/buildings/", 200),
            ("/api/v1/members/", 403),
            ("/api/v1/installs/", 200),
            ("/api/v1/requests/", 200),
        ]

        for route, code in routes:
            response = self.c.get(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
            )


class TestViewsCodesAdmin(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )

    def test_all_views_codes_admin(self):
        self.c.login(username="admin", password="admin_password")

        routes = [
            ("/api/v1/", 200),
            ("/api/v1", 301),
            ("/api/v1/buildings/", 200),
            ("/api/v1/members/", 200),
            ("/api/v1/installs/", 200),
            ("/api/v1/requests/", 200),
        ]

        for route, code in routes:
            response = self.c.get(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
            )

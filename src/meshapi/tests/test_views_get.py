from django.contrib.auth.models import User
from django.test import Client, TestCase
from rest_framework.authtoken.models import Token

from meshapi.tests.group_helpers import create_installer_group


class TestViewsGetUnauthenticated(TestCase):
    c = Client()

    def test_views_get_unauthenticated(self):
        routes = [
            ("/api/v1/", 200),
            ("/api/v1", 301),
            ("/api/v1/buildings/", 200),
            ("/api/v1/members/", 401),
            ("/api/v1/installs/", 200),
        ]

        for route, code in routes:
            response = self.c.get(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
            )


class TestViewsGetInstaller(TestCase):
    c = Client()

    def setUp(self):
        self.installer_user = User.objects.create_user(
            username="installer", password="installer_password", email="installer@example.com"
        )
        installer_group = create_installer_group()
        self.installer_user.groups.add(installer_group)

    def test_views_get_installer(self):
        self.c.login(username="installer", password="installer_password")

        routes = [
            ("/api/v1/", 200),
            ("/api/v1", 301),
            ("/api/v1/buildings/", 200),
            ("/api/v1/members/", 200),
            ("/api/v1/installs/", 200),
        ]

        for route, code in routes:
            response = self.c.get(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
            )


class TestViewsGetAdmin(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )

    def test_views_get_admin(self):
        self.c.login(username="admin", password="admin_password")

        routes = [
            ("/api/v1/", 200),
            ("/api/v1", 301),
            ("/api/v1/buildings/", 200),
            ("/api/v1/members/", 200),
            ("/api/v1/installs/", 200),
        ]

        for route, code in routes:
            response = self.c.get(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
            )

    def test_views_get_admin_token(self):
        t = Client()
        token = Token.objects.create(user=self.admin_user)

        routes = [
            ("/api/v1/", 200),
            ("/api/v1", 301),
            ("/api/v1/buildings/", 200),
            ("/api/v1/members/", 200),
            ("/api/v1/installs/", 200),
        ]

        for route, code in routes:
            response = t.get(
                route,
                HTTP_AUTHORIZATION=f"Token {token.key}",
            )
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
            )

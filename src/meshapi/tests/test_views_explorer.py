from django.contrib.auth.models import Group, User
from django.test import TestCase

from meshapi.tests.group_helpers import create_groups


class TestViewsExplorer(TestCase):
    databases = "__all__"

    def setUp(self):
        self.explorer_user = User.objects.create_user(
            username="exploreruser", password="explorer_password", email="explorer@example.com"
        )
        create_groups()
        self.explorer_user.groups.add(Group.objects.get(name="Explorer Access"))

    def test_views_get_explorer(self):
        self.client.login(username="exploreruser", password="explorer_password")

        routes = [
            ("/explorer/", 200),
        ]

        for route, code in routes:
            response = self.client.get(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
            )

    def test_views_get_explorer_unauthenticated(self):
        self.client.logout()  # log out just in case

        routes = [
            ("/explorer/", 302),
        ]

        for route, code in routes:
            response = self.client.get(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
            )

    def test_views_post_explorer_playground(self):
        self.client.login(username="exploreruser", password="explorer_password")

        route = "/explorer/play/"
        code = 200
        post_data = {"sql": "SELECT+*+FROM+meshapi_member;"}

        response = self.client.post(route, data=post_data)
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for {route}. Should be {code}, but got {response.status_code}",
        )

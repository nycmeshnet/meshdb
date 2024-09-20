from django.contrib.auth.models import Group, User
from django.test import TestCase

from meshapi.tests.group_helpers import create_groups


class TestViewsGetExplorer(TestCase):
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

from django.test import Client, TestCase
from django.contrib.auth.models import User

class TestJoinForm(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def _test_list(self, route, code):
        response = self.c.get(route)
        self.assertEqual(
            code,
            response.status_code,
            f"Could not view {route} in the admin panel."
        )

    def test_list_building(self):
        self._test_list("/admin/meshapi/building/", 200)

    def test_list_member(self):
        self._test_list("/admin/meshapi/member/", 200)

    def test_list_install(self):
        self._test_list("/admin/meshapi/install/", 200)

    def test_list_link(self):
        self._test_list("/admin/meshapi/link/", 200)

    def test_list_sector(self):
        self._test_list("/admin/meshapi/sector/", 200)


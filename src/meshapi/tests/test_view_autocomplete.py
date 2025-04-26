from django.contrib.auth.models import User
from django.test import Client, TestCase


class TestViewAutocomplete(TestCase):
    c = Client()
    a = Client()  # anon client

    def setUp(self) -> None:
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def test_views_get_autocomplete(self):
        r = self.c.get("/member-autocomplete/")
        code = 200
        self.assertEqual(code, r.status_code)

    # The view just returns empty if it's unauthenticated
    def test_views_get_autocomplete_unauthenticated(self):
        r = self.a.get("/member-autocomplete/")

        # We'll get a 200, but the response will be empty
        code = 200
        self.assertEqual(code, r.status_code)
        j = r.json()
        self.assertEqual([], j["results"])

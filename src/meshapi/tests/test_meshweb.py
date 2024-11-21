from django.test import TestCase


class TestViewsGetUnauthenticated(TestCase):
    def test_landing_page_get_unauthenticated(self):
        response = self.client.get("/")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect for /. Should be 200, but got {response.status_code}",
        )

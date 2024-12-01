from .integ_test_case import IntegTestCase


class TestAPI200(IntegTestCase):
    def test_api_200(self):
        response = self.authed_session.get(self.get_url("/api/v1/"))
        self.assertEqual(response.status_code, 200)

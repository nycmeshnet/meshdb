from django.test import TestCase


class TestDevice(TestCase):
    def test_docs_200_unauth(self):
        self.assertEqual(self.client.get("/api-docs/swagger/").status_code, 200)
        self.assertEqual(self.client.get("/api-docs/redoc/").status_code, 200)
        self.assertEqual(self.client.get("/api-docs/openapi3.json").status_code, 200)

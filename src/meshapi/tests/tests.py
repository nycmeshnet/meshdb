from django.test import TestCase, Client

# Create your tests here.

class TestViewsCodesUnauthenticated(TestCase):
    c = Client()
    def test_api_root(self):
        response = self.c.get("/api/v1/")
        assert response.status_code == 200
    def test_api_root_redirect(self):
        response = self.c.get("/api/v1")
        assert response.status_code == 301
    def test_api_buildings(self):
        response = self.c.get("/api/v1/buildings/")
        assert response.status_code == 200
    def test_api_members(self):
        response = self.c.get("/api/v1/members/")
        assert response.status_code == 403

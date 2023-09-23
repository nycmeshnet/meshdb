from django.test import TestCase, Client
from django.contrib.auth.models import User

# Create your tests here.


class TestViewsCodesUnauthenticated(TestCase):
    c = Client()

    def test_all_views_codes_unauthenticated(self):
        response = self.c.get("/api/v1/")
        assert response.status_code == 200
        response = self.c.get("/api/v1")
        assert response.status_code == 301
        response = self.c.get("/api/v1/buildings/")
        assert response.status_code == 200
        response = self.c.get("/api/v1/members/")
        assert response.status_code == 403
        response = self.c.get("/api/v1/installs/")
        assert response.status_code == 200
        response = self.c.get("/api/v1/requests/")
        assert response.status_code == 200


class TestViewsCodesAdmin(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )

    def test_all_views_codes_admin(self):
        self.c.login(username="admin", password="admin_password")
        response = self.c.get("/api/v1/")
        assert response.status_code == 200
        response = self.c.get("/api/v1")
        assert response.status_code == 301
        response = self.c.get("/api/v1/buildings/")
        assert response.status_code == 200
        response = self.c.get("/api/v1/members/")
        assert response.status_code == 200
        response = self.c.get("/api/v1/installs/")
        assert response.status_code == 200
        response = self.c.get("/api/v1/requests/")
        assert response.status_code == 200

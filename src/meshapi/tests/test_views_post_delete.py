import json

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase

from .sample_data import sample_building, sample_install, sample_member


def assert_correct_response(test, response, code):
    path = response.request.get("PATH_INFO")
    content = response.content.decode("utf-8")
    test.assertEqual(
        code,
        response.status_code,
        f"status code incorrect. {path} should be {code}, but got {response.status_code}. {content}",
    )


# Wow so brittle
def get_first_id(client, route, field="id"):
    return json.loads(client.get(route).content.decode("utf-8")).get("results")[0].get(field)


class TestViewsPostDeleteUnauthenticated(TestCase):
    c = Client()

    def test_views_post_unauthenticated(self):
        response = self.c.post("/api/v1/members/", sample_member)
        assert_correct_response(self, response, 403)

        response = self.c.post("/api/v1/buildings/", sample_building)
        assert_correct_response(self, response, 403)

        response = self.c.post("/api/v1/installs/", sample_install)
        assert_correct_response(self, response, 403)

    def test_views_delete_unauthenticated(self):
        response = self.c.delete(f"/api/v1/installs/1/")
        assert_correct_response(self, response, 403)

        response = self.c.delete(f"/api/v1/members/1/")
        assert_correct_response(self, response, 403)

        response = self.c.delete(f"/api/v1/buildings/1/")
        assert_correct_response(self, response, 403)


class TestViewsPostDeleteInstaller(TestCase):
    c = Client()
    admin_c = Client()

    def setUp(self):
        self.installer_user = User.objects.create_user(
            username="installer", password="installer_password", email="installer@example.com"
        )
        installer_group, _ = Group.objects.get_or_create(name="Installer")
        self.installer_user.groups.add(installer_group)
        self.c.login(username="installer", password="installer_password")

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

    def test_views_post_installer(self):
        response = self.c.post("/api/v1/members/", sample_member)
        assert_correct_response(self, response, 403)

        response = self.c.post("/api/v1/buildings/", sample_building)
        assert_correct_response(self, response, 403)

        # Add those resources as admin to make sure the rest of the routes work
        self.admin_c.post("/api/v1/members/", sample_member)
        self.admin_c.post("/api/v1/buildings/", sample_building)

        member_id = get_first_id(self.c, "/api/v1/members/")
        building_id = get_first_id(self.c, "/api/v1/buildings/")
        sample_install_copy = sample_install.copy()
        sample_install_copy["member"] = member_id
        sample_install_copy["building"] = building_id

        response = self.c.post("/api/v1/installs/", sample_install_copy)
        assert_correct_response(self, response, 201)

    def test_views_delete_installer(self):
        response = self.c.delete(f"/api/v1/installs/1/")
        assert_correct_response(self, response, 403)

        response = self.c.delete(f"/api/v1/members/1/")
        assert_correct_response(self, response, 403)

        response = self.c.delete(f"/api/v1/buildings/1/")
        assert_correct_response(self, response, 403)


class TestViewsPostDeleteAdmin(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def test_views_post_admin(self):
        response = self.c.post("/api/v1/members/", sample_member)
        assert_correct_response(self, response, 201)

        member_id = get_first_id(self.c, "/api/v1/members/")
        response = self.c.post("/api/v1/buildings/", sample_building)
        assert_correct_response(self, response, 201)
        building_id = get_first_id(self.c, "/api/v1/buildings/")

        sample_install_copy = sample_install.copy()
        sample_install_copy["member"] = member_id
        sample_install_copy["building"] = building_id
        response = self.c.post("/api/v1/installs/", sample_install_copy)
        assert_correct_response(self, response, 201)
        # XXX: This is how I know that getting the install number from the API is working
        install_id = get_first_id(self.c, "/api/v1/installs/", "install_number")

        # Now delete
        response = self.c.delete(f"/api/v1/installs/{install_id}/")
        assert_correct_response(self, response, 204)

        response = self.c.delete(f"/api/v1/members/{member_id}/")
        assert_correct_response(self, response, 204)

        response = self.c.delete(f"/api/v1/buildings/{building_id}/")
        assert_correct_response(self, response, 204)

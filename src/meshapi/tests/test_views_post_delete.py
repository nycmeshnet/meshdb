import json
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group

from .sample_data import sample_member, sample_building, sample_install


def assert_correct_response(test, response, code):
    path = response.request.get("PATH_INFO")
    content = response.content.decode("utf-8")
    test.assertEqual(
        code,
        response.status_code,
        f"status code incorrect. {path} should be {code}, but got {response.status_code}. {content}",
    )


# Wow so brittle
def get_first_id(client, route):
    return json.loads(client.get(route).content.decode("utf-8")).get("results")[0].get("id")


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
        sample_install["member_id"] = member_id
        sample_install["building_id"] = building_id

        response = self.c.post("/api/v1/installs/", sample_install)
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

        sample_install["member_id"] = member_id
        sample_install["building_id"] = building_id
        response = self.c.post("/api/v1/installs/", sample_install)
        assert_correct_response(self, response, 201)
        install_id = get_first_id(self.c, "/api/v1/installs/")

        # FIXME: For some reason this fails as a separate test
        # I have literally no idea why. Could be an issue with
        # the test DB. None of the other tests hit this, probably
        # because nobody is allowed to do things that would warrant
        # cross-function testing. Fair enough I suppose.
        response = self.c.delete(f"/api/v1/installs/{install_id}/")
        assert_correct_response(self, response, 204)

        response = self.c.delete(f"/api/v1/members/{member_id}/")
        assert_correct_response(self, response, 204)

        response = self.c.delete(f"/api/v1/buildings/{building_id}/")
        assert_correct_response(self, response, 204)

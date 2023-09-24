from django.test import TestCase, Client
from django.contrib.auth.models import User, Group

from .sample_data import sample_member, sample_building, sample_install, sample_request


def assert_correct_response(test, response, code):
    path = response.request.get("PATH_INFO")
    content = response.content.decode("utf-8")
    test.assertEqual(
        code,
        response.status_code,
        f"status code incorrect. {path} should be {code}, but got {response.status_code}. {content}",
    )


class TestViewsPostDeleteUnauthenticated(TestCase):
    c = Client()

    def test_views_post_unauthenticated(self):
        response = self.c.post("/api/v1/members/", sample_member)
        assert_correct_response(self, response, 403)

        response = self.c.post("/api/v1/buildings/", sample_building)
        assert_correct_response(self, response, 403)

        response = self.c.post("/api/v1/installs/", sample_install)
        assert_correct_response(self, response, 403)

        response = self.c.post("/api/v1/requests/", sample_request)
        assert_correct_response(self, response, 403)  # 400 because previous requests failed

    def test_views_delete_unauthenticated(self):
        sample_request_id = sample_request.get("id")
        response = self.c.delete(f"/api/v1/requests/{sample_request_id}/")
        assert_correct_response(self, response, 403)

        sample_install_id = sample_install.get("id")
        response = self.c.delete(f"/api/v1/installs/{sample_install_id}/")
        assert_correct_response(self, response, 403)

        sample_member_id = sample_member.get("id")
        response = self.c.delete(f"/api/v1/members/{sample_member_id}/")
        assert_correct_response(self, response, 403)

        sample_building_id = sample_building.get("id")
        response = self.c.delete(f"/api/v1/buildings/{sample_building_id}/")
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

        response = self.c.post("/api/v1/installs/", sample_install)
        assert_correct_response(self, response, 201)

        response = self.c.post("/api/v1/requests/", sample_request)
        assert_correct_response(self, response, 403)

    def test_views_delete_installer(self):
        sample_request_id = sample_request.get("id")
        response = self.c.delete(f"/api/v1/requests/{sample_request_id}/")
        assert_correct_response(self, response, 403)

        sample_install_id = sample_install.get("id")
        response = self.c.delete(f"/api/v1/installs/{sample_install_id}/")
        assert_correct_response(self, response, 403)

        sample_member_id = sample_member.get("id")
        response = self.c.delete(f"/api/v1/members/{sample_member_id}/")
        assert_correct_response(self, response, 403)

        sample_building_id = sample_building.get("id")
        response = self.c.delete(f"/api/v1/buildings/{sample_building_id}/")
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

        response = self.c.post("/api/v1/buildings/", sample_building)
        assert_correct_response(self, response, 201)

        response = self.c.post("/api/v1/installs/", sample_install)
        assert_correct_response(self, response, 201)

        response = self.c.post("/api/v1/requests/", sample_request)
        assert_correct_response(self, response, 201)

        # FIXME: For some reason this fails as a separate test
        # I have literally no idea why. Could be an issue with
        # the test DB. None of the other tests hit this, probably
        # because nobody is allowed to do things that would warrant
        # cross-function testing. Fair enough I suppose.
        sample_request_id = sample_request.get("id")
        response = self.c.delete(f"/api/v1/requests/{sample_request_id}/")
        assert_correct_response(self, response, 204)

        sample_install_id = sample_install.get("id")
        response = self.c.delete(f"/api/v1/installs/{sample_install_id}/")
        assert_correct_response(self, response, 204)

        sample_member_id = sample_member.get("id")
        response = self.c.delete(f"/api/v1/members/{sample_member_id}/")
        assert_correct_response(self, response, 204)

        sample_building_id = sample_building.get("id")
        response = self.c.delete(f"/api/v1/buildings/{sample_building_id}/")
        assert_correct_response(self, response, 204)

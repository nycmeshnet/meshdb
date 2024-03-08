import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import Building, Install, Member
from .group_helpers import create_groups
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
        _, installer_group, _ = create_groups()
        self.installer_user.groups.add(installer_group)
        self.c.login(username="installer", password="installer_password")

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

    def test_views_post_put_installer(self):
        # Add those resources without HTTP, so we have something to PUT against
        member = Member(**sample_member)
        member.save()
        building = Building(**sample_building)
        building.save()
        sample_install_copy = sample_install.copy()
        sample_install_copy["building"] = building
        sample_install_copy["member"] = member
        install = Install(**sample_install_copy)
        install.save()

        sample_member_changed = sample_member.copy()
        sample_member_changed["name"] = "Chom2"
        response = self.c.post("/api/v1/members/", sample_member_changed)
        assert_correct_response(self, response, 403)
        response = self.c.put(
            f"/api/v1/members/{member.id}/",
            sample_member_changed,
            content_type="application/json",
        )
        assert_correct_response(self, response, 200)

        # Make sure the member was actually changed
        member.refresh_from_db()
        assert member.name == "Chom2"

        sample_building_changed = sample_member.copy()
        sample_building_changed["site_name"] = "Chom2"
        response = self.c.post("/api/v1/buildings/", sample_building_changed)
        assert_correct_response(self, response, 403)
        response = self.c.put(
            f"/api/v1/buildings/{building.id}/",
            sample_building_changed,
            content_type="application/json",
        )
        assert_correct_response(self, response, 403)

        sample_install_changed = sample_install.copy()
        sample_install_changed["install_number"] = install.install_number
        sample_install_changed["notes"] += "\n abcdef"  # Change something
        sample_install_changed["member"] = member.id
        sample_install_changed["building"] = building.id

        response = self.c.post("/api/v1/installs/", sample_install_changed)
        assert_correct_response(self, response, 403)
        response = self.c.put(
            f"/api/v1/installs/{install.install_number}/",
            sample_install_changed,
            content_type="application/json",
        )
        assert_correct_response(self, response, 200)

        # Make sure the install was actually changed
        install.refresh_from_db()
        assert install.notes.endswith("\n abcdef")

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

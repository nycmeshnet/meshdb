import json

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase

from meshapi.models import Building, Install, Member
from meshapi.tests.sample_data import sample_building, sample_install, sample_member


def setup_objects():
    member_obj = Member(**sample_member)
    member_obj.save()
    building = sample_building.copy()
    building_obj = Building(**building)
    building_obj.save()
    inst = sample_install.copy()

    if inst["abandon_date"] == "":
        inst["abandon_date"] = None

    inst["building"] = building_obj
    inst["member"] = member_obj
    inst["install_number"] = 2000
    install_obj = Install(**inst)
    install_obj.save()

    return member_obj, building_obj, install_obj


class TestViewsGetLimitedPermissions(TestCase):
    c = Client()

    def setUp(self):
        # Create sample data
        self.member, self.building, self.install = setup_objects()

        self.no_member_perm_user = User.objects.create_user(
            username="limited_install", password="password", email="installer@example.com"
        )
        self.no_member_perm_user.user_permissions.add(Permission.objects.get(codename="view_install"))
        self.no_member_perm_user.user_permissions.add(Permission.objects.get(codename="view_building"))

        self.no_install_perm_user = User.objects.create_user(
            username="limited_member", password="password", email="installer@example.com"
        )
        self.no_install_perm_user.user_permissions.add(Permission.objects.get(codename="view_member"))
        self.no_install_perm_user.user_permissions.add(Permission.objects.get(codename="view_building"))

    def test_views_get_install(self):
        self.c.login(username="limited_install", password="password")

        response = self.c.get(f"/api/v1/installs/{self.install.id}/").json()
        self.assertEqual(response["unit"], "3")
        self.assertEqual(response["member"], str(self.member.id))
        self.assertEqual(response["building"], str(self.building.id))

        self.c.login(username="limited_member", password="password")

        response = self.c.get(f"/api/v1/installs/{self.install.id}/")
        self.assertEqual(response.status_code, 403)

    def test_views_get_member(self):
        self.c.login(username="limited_install", password="password")

        response = self.c.get(f"/api/v1/members/{self.member.id}/")
        self.assertEqual(response.status_code, 403)

        self.c.login(username="limited_member", password="password")

        response = self.c.get(f"/api/v1/members/{self.member.id}/").json()
        self.assertEqual(response["primary_email_address"], "john.smith@example.com")
        self.assertEqual(response["installs"], [{"install_number": 2000, "id": str(self.install.id)}])

    def test_views_get_building(self):
        self.c.login(username="limited_install", password="password")

        response = self.c.get(f"/api/v1/buildings/{self.building.id}/").json()
        self.assertEqual(response["bin"], 8888)
        self.assertEqual(response["installs"], [{"install_number": 2000, "id": str(self.install.id)}])

        self.c.login(username="limited_member", password="password")

        response = self.c.get(f"/api/v1/buildings/{self.building.id}/").json()
        self.assertEqual(response["bin"], 8888)
        self.assertEqual(response["installs"], [{"install_number": 2000, "id": str(self.install.id)}])


class TestViewsGetAdmin(TestCase):
    c = Client()

    def setUp(self):
        # Create sample data
        self.member, self.building, self.install = setup_objects()

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )

    def test_views_get_install(self):
        self.c.login(username="admin", password="admin_password")

        response = self.c.get(f"/api/v1/installs/{self.install.id}/").json()
        self.assertEqual(response["unit"], "3")
        self.assertEqual(response["member"], str(self.member.id))
        self.assertEqual(response["building"], str(self.building.id))

    def test_views_get_member(self):
        self.c.login(username="admin", password="admin_password")

        response = self.c.get(f"/api/v1/members/{self.member.id}/").json()
        self.assertEqual(response["primary_email_address"], "john.smith@example.com")
        self.assertEqual(response["all_email_addresses"], ["john.smith@example.com"])
        self.assertEqual(response["installs"], [{"install_number": 2000, "id": str(self.install.id)}])

    def test_views_get_building(self):
        self.c.login(username="admin", password="admin_password")

        response = self.c.get(f"/api/v1/buildings/{self.building.id}/").json()
        self.assertEqual(response["bin"], 8888)
        self.assertEqual(response["installs"], [{"install_number": 2000, "id": str(self.install.id)}])


class TestViewsPutAdmin(TestCase):
    c = Client()

    def setUp(self):
        # Create sample data
        self.member, self.building, self.install = setup_objects()

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )

    def test_views_put_new_install_with_pk(self):
        self.c.login(username="admin", password="admin_password")

        inst = sample_install.copy()

        if inst["abandon_date"] == "":
            inst["abandon_date"] = None

        inst["building"] = str(self.building.id)
        inst["member"] = str(self.member.id)
        inst["install_number"] = 2001

        response = self.c.post("/api/v1/installs/", inst)
        self.assertEqual(response.status_code, 201)

        install = Install.objects.get(install_number=response.json()["install_number"])
        self.assertEqual(install.member.id, self.member.id)
        self.assertEqual(install.member.primary_email_address, "john.smith@example.com")
        self.assertEqual(install.building.id, self.building.id)
        self.assertEqual(install.building.bin, 8888)

    def test_views_post_new_install_with_nested_data_not_allowed(self):
        self.c.login(username="admin", password="admin_password")

        inst = sample_install.copy()

        if inst["abandon_date"] == "":
            inst["abandon_date"] = None

        inst["building"] = self.building.id
        inst["member"] = sample_member
        inst["install_number"] = 2001

        response = self.c.post("/api/v1/installs/", inst)
        self.assertEqual(response.status_code, 400)

    def test_views_put_install_with_nested_data_not_allowed(self):
        self.c.login(username="admin", password="admin_password")

        inst = sample_install.copy()

        if inst["abandon_date"] == "":
            inst["abandon_date"] = None

        inst["building"] = str(self.building.id)
        inst["member"] = sample_member
        inst["install_number"] = 2000

        response = self.c.put(f"/api/v1/installs/{self.install.id}/", json.dumps(inst), content_type="application/json")
        self.assertEqual(response.status_code, 400)

import json
import uuid

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from meshapi.models import Building, Install, Member
from meshapi.tests.sample_data import sample_building, sample_install, sample_member


class TestInstallModel(TestCase):
    def setUp(self):
        self.sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        self.sample_install_copy["building"] = self.building_1

        self.member = Member(**sample_member)
        self.member.save()
        self.sample_install_copy["member"] = self.member

    def test_construct_install_no_id_no_install_number(self):
        install = Install(**self.sample_install_copy)
        install.save()

        self.assertIsNotNone(install.id)
        self.assertIsNotNone(install.install_number)
        self.assertGreater(install.install_number, 0)

    def test_construct_install_no_id_yes_install_number(self):
        install = Install(**self.sample_install_copy, install_number=45)
        install.save()

        self.assertIsNotNone(install.id)
        self.assertEqual(install.install_number, 45)

        install2 = Install(**self.sample_install_copy)
        install2.install_number = 89
        install2.save()

        self.assertIsNotNone(install2.id)
        self.assertEqual(install2.install_number, 89)

    def test_construct_install_yes_id_no_install_number(self):
        install = Install(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            **self.sample_install_copy,
        )
        install.save()

        self.assertEqual(install.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertIsNotNone(install.install_number)
        self.assertGreater(install.install_number, 0)

    def test_construct_install_yes_id_yes_install_number(self):
        install = Install(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            install_number=45,
            **self.sample_install_copy,
        )
        install.save()

        self.assertEqual(install.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(install.install_number, 45)

    def test_update_install_with_install_number(self):
        install = Install(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            install_number=45,
            **self.sample_install_copy,
        )
        install.save()

        self.assertEqual(install.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(install.install_number, 45)

        install.install_number = 78
        with pytest.raises(ValidationError):
            install.save()

        install.refresh_from_db()
        self.assertEqual(install.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(install.install_number, 45)

    def test_update_install_unset_install_number(self):
        install = Install(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            install_number=45,
            **self.sample_install_copy,
        )
        install.save()

        self.assertEqual(install.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(install.install_number, 45)

        install.install_number = None
        with pytest.raises(ValidationError):
            install.save()

        install.refresh_from_db()
        self.assertEqual(install.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(install.install_number, 45)

    def test_osticket_number_leading_zeros(self):
        install = Install(**self.sample_install_copy)
        install.ticket_number = "00123"
        install.save()

        install_copy = Install.objects.get(id=install.id)
        self.assertEqual(install_copy.ticket_number, "00123")


class TestInstallAPI(TestCase):
    def setUp(self):
        self.sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()

        self.member = Member(**sample_member)
        self.member.save()

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.client.login(username="admin", password="admin_password")

        self.install1 = Install(
            **self.sample_install_copy,
            building=self.building_1,
            member=self.member,
        )
        self.install1.save()

        self.install28 = Install(
            **self.sample_install_copy,
            install_number=28,
            building=self.building_1,
            member=self.member,
        )
        self.install28.save()

    def test_install_number_readonly_on_create(self):
        response = self.client.post(
            "/api/v1/installs/",
            {
                **self.sample_install_copy,
                "install_number": 123,
                "member": {"id": str(self.member.id)},
                "building": {"id": str(self.building_1.id)},
            },
            content_type="application/json",
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertNotEqual(response_obj["install_number"], 123)

        response = self.client.post(
            "/api/v1/installs/",
            {
                **self.sample_install_copy,
                "install_number": None,
                "member": {"id": str(self.member.id)},
                "building": {"id": str(self.building_1.id)},
            },
            content_type="application/json",
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertIsNotNone(response_obj["install_number"])

        response = self.client.post(
            "/api/v1/installs/",
            {
                **self.sample_install_copy,
                "member": {"id": str(self.member.id)},
                "building": {"id": str(self.building_1.id)},
            },
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertIsNotNone(response_obj["install_number"])

    def test_broken_install(self):
        response = self.client.post(
            "/api/v1/installs/",
            {
                **self.sample_install_copy,
                "member": {"id": str(self.member.id)},
                # Missing building
            },
            content_type="application/json",
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_cant_steal_taken_install_number(self):
        response = self.client.post(
            "/api/v1/installs/",
            {
                **self.sample_install_copy,
                "install_number": 1,
                "member": {"id": str(self.member.id)},
                "building": {"id": str(self.building_1.id)},
            },
            content_type="application/json",
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertNotEqual(response_obj["install_number"], 1)
        self.assertEqual(len(Install.objects.all()), 3)

    def test_get_install_by_id(self):
        response = self.client.get(f"/api/v1/installs/{self.install1.id}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["unit"], "3")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], "Referral: Read about it on the internet")

    def test_get_install_by_num(self):
        response = self.client.get(f"/api/v1/installs/{self.install1.install_number}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["unit"], "3")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], "Referral: Read about it on the internet")

    def test_modify_install_by_id(self):
        response = self.client.patch(
            f"/api/v1/installs/{self.install1.id}/",
            {"notes": "New notes! Wheee"},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["unit"], "3")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], "New notes! Wheee")

    def test_modify_install_by_num(self):
        response = self.client.patch(
            f"/api/v1/installs/{self.install1.install_number}/",
            {"notes": "New notes! Wheee"},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["unit"], "3")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], "New notes! Wheee")

    def test_cant_modify_existing_install_num(self):
        response = self.client.patch(
            f"/api/v1/installs/{self.install28.id}/",
            {"install_num": 123},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["install_number"], 28)
        self.install28.refresh_from_db()
        self.assertEqual(self.install28.install_number, 28)

        response = self.client.patch(
            f"/api/v1/installs/{self.install28.id}/",
            {"node": None},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["install_number"], 28)
        self.install28.refresh_from_db()
        self.assertEqual(self.install28.install_number, 28)

    def test_cant_remove_existing_install_num(self):
        response = self.client.put(
            f"/api/v1/installs/{self.install28.id}/",
            {
                **self.sample_install_copy,
                "member": {"id": str(self.member.id)},
                "building": {"id": str(self.building_1.id)},
            },
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["install_number"], 28)
        self.install28.refresh_from_db()
        self.assertEqual(self.install28.install_number, 28)

    def test_delete_install_by_id(self):
        install_number = self.install1.install_number
        response = self.client.delete(f"/api/v1/installs/{self.install1.id}/")

        code = 204
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        self.assertEqual(0, len(Install.objects.filter(install_number=install_number)))

    def test_delete_install_by_number(self):
        install_number = self.install1.install_number
        response = self.client.delete(f"/api/v1/installs/{self.install1.install_number}/")

        code = 204
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        self.assertEqual(0, len(Install.objects.filter(install_number=install_number)))

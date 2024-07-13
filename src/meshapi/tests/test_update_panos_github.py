import os
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase

from meshapi.models import Building, Install, Member
from meshapi.views.panoramas import (
    BadPanoramaTitle,
    PanoramaTitle,
    get_head_tree_sha,
    list_files_in_git_directory,
    set_panoramas,
)

from .sample_data import sample_building, sample_install, sample_member


class TestPanoPipeline(TestCase):
    c = Client()

    def setUp(self):
        sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        sample_install_copy["building"] = self.building_1

        self.member = Member(**sample_member)
        self.member.save()
        sample_install_copy["member"] = self.member

        self.install = Install(**sample_install_copy)
        self.install.save()

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

    def test_set_panoramas(self):
        # Fabricate some fake panorama photos
        n = self.install.install_number
        panos = {n: PanoramaTitle.from_filenames([f"{n}.jpg", f"{n}a.jpg"])}

        set_panoramas(panos)

        # Now check that that worked.
        building = Building.objects.get(id=self.install.building.id)
        saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
        ]
        self.assertEqual(saved_panoramas, building.panoramas)

    def test_update_panoramas(self):
        # Fabricate some fake panorama photos
        n = self.install.install_number
        panos = {n: PanoramaTitle.from_filenames([f"{n}.jpg", f"{n}a.jpg"])}

        set_panoramas(panos)

        # Now check that that worked.
        building = Building.objects.get(id=self.install.building.id)
        saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
        ]
        self.assertEqual(saved_panoramas, building.panoramas)

        # Now add one from the previous list, and a new one.
        panos = {n: PanoramaTitle.from_filenames([f"{n}.jpg", f"{n}b.jpg"])}

        set_panoramas(panos)

        # Now check that that worked. We want all three
        building = Building.objects.get(id=self.install.building.id)
        saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
            f"https://node-db.netlify.app/panoramas/{n}b.jpg",
        ]
        self.assertEqual(saved_panoramas, building.panoramas)


class TestPanoAuthentication(TestCase):
    c = Client()
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

    def test_update_panoramas_unauthenticated(self):
        response = self.c.get("/api/v1/update-panoramas/")
        code = 403
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    # This tests the endpoint, but not the actual full pipeline.
    @patch("meshapi.views.os.environ.get")
    @patch("meshapi.views.requests.get")
    def test_update_panoramas_authenticated(self, mock_requests, mock_os):
        fake_dir = "data/panoramas"
        mock_os.return_value = fake_dir

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "commit": {"commit": {"tree": {"sha": "4"}}},
            "tree": [{"type": "blob", "path": f"{fake_dir}/lol.txt"}],
        }
        mock_requests.return_value = mock_response

        response = self.admin_c.post("/api/v1/update-panoramas/")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestPanoUtils(TestCase):
    def setUp(self):
        # Check that we have all the environment variables we need
        self.owner = os.environ.get("PANO_REPO_OWNER") or "nycmeshnet"
        self.repo = os.environ.get("PANO_REPO") or "node-db"
        self.branch = os.environ.get("PANO_BRANCH") or "master"
        self.directory = os.environ.get("PANO_DIR") or "data/panoramas"
        self.host_url = os.environ.get("PANO_HOST") or "http://example.com"
        self.token = os.environ.get("PANO_GITHUB_TOKEN") or "4"

    def test_parse_pano_title(self):
        test_cases = {
            # Normal cases
            "9035.jpg": PanoramaTitle("9035.jpg", False, "9035", ""),
            "9035a.jpg": PanoramaTitle("9035a.jpg", False, "9035", "a"),
            # Network Numbers
            "nn632.jpg": PanoramaTitle("nn632.jpg", True, "632", ""),
            # Hypotheticals
            "903590232289437230978078923047589204710578901457891230587abcdefghijklmnopqrstuv.jpg": PanoramaTitle(
                "903590232289437230978078923047589204710578901457891230587abcdefghijklmnopqrstuv.jpg",
                False,
                "903590232289437230978078923047589204710578901457891230587",
                "abcdefghijklmnopqrstuv",
            ),
            "nn903590232289437230978078923047589204710578901457891230587abcdefghijklmnopqrstuv.jpg": PanoramaTitle(
                "nn903590232289437230978078923047589204710578901457891230587abcdefghijklmnopqrstuv.jpg",
                True,
                "903590232289437230978078923047589204710578901457891230587",
                "abcdefghijklmnopqrstuv",
            ),
            "888.jpg.jpg": PanoramaTitle("888.jpg.jpg", False, "888", ".jpg"),
            # Dumb edge cases
            "IMG_5869.jpg": PanoramaTitle("IMG_5869.jpg", False, "5869", ""),
            " 11001d.jpg": PanoramaTitle(" 11001d.jpg", False, "11001", "d"),
        }
        for case, expected in test_cases.items():
            result = PanoramaTitle.from_filename(case)
            self.assertEqual(result, expected, f"Expected: {expected}. Result: {result}.")
            # TODO: Assert that all the URL functions and stuff work

    # The GitHub does not have a perfectly uniform set of files.
    def test_parse_pano_bad_title(self):
        with self.assertRaises(BadPanoramaTitle):
            test_cases = {
                "Icon\r": ("", ""),
                "": ("", ""),
                "chom": ("", ""),
            }
            for case, _ in test_cases.items():
                PanoramaTitle.from_filename(case)

    # Crude test to sanity check that fn
    # Also this API likes to give me 500s and it would be nice to know if that was
    # a common enough thing to disrupt tests. I guess this is designed to detect
    # flakiness
    @patch("meshapi.views.requests.get")
    def test_github_API(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "commit": {"commit": {"tree": {"sha": "4"}}},
            "tree": [{"type": "blob", "path": f"{self.directory}/lol.txt"}],
        }
        mock_requests.return_value = mock_response

        head_tree_sha = get_head_tree_sha(self.owner, self.repo, self.branch)
        assert head_tree_sha is not None
        assert head_tree_sha == "4"

        panorama_files = list_files_in_git_directory(self.owner, self.repo, self.directory, head_tree_sha)
        assert panorama_files is not None
        assert len(panorama_files) == 1
        assert panorama_files[0] == "lol.txt"

import os
from unittest import mock
from unittest.mock import MagicMock, patch

from django.core import management
from django.test import TestCase

from meshapi.models import Building, Install, Member
from meshapi.models.node import Node
from meshapi.util.panoramas import (
    BadPanoramaTitle,
    GitHubError,
    PanoramaTitle,
    get_head_tree_sha,
    list_files_in_git_directory,
    save_building_panoramas,
    set_panoramas,
    sync_github_panoramas,
)

from .sample_data import sample_building, sample_install, sample_member, sample_node


class TestSyncPanoramasCommand(TestCase):
    # This should hit the github api and then just not set anything in an empty db
    @mock.patch("meshapi.util.panoramas.get_head_tree_sha", return_value="mockedsha")
    @mock.patch("meshapi.util.panoramas.list_files_in_git_directory", return_value=["713a.jpg", "713b.jpg"])
    def test_sync_panoramas(self, get_head_tree_sha_function, list_files_in_git_directory_function):
        management.call_command("sync_panoramas")


class TestPanoPipeline(TestCase):
    def setUp(self):
        sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        sample_install_copy["building"] = self.building_1

        self.member = Member(**sample_member)
        self.member.save()
        sample_install_copy["member"] = self.member

        self.node = Node(**sample_node)
        self.node.save()
        sample_install_copy["node"] = self.node

        self.install = Install(**sample_install_copy)
        self.install.save()

    def test_set_panoramas(self):
        # Fabricate some fake panorama photos
        n = self.install.install_number
        nn = self.install.node.network_number
        panos = {
            "69420": PanoramaTitle.from_filenames(["69420.jpg", "69420a.jpg"]),  # Throw some BS ones in there
            str(n): PanoramaTitle.from_filenames([f"{n}.jpg", f"{n}a.jpg"]),
            "": PanoramaTitle.from_filenames(["6942029019023190.jpg"]),  # Throw some BS ones in there
            f"nn{nn}": PanoramaTitle.from_filenames([f"nn{nn}.jpg", f"nn{nn}a.jpg", f"nn{nn}b.jpg"]),
        }

        set_panoramas(panos)

        # Now check that that worked.
        building = Building.objects.get(id=self.install.building.id)
        saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
            f"https://node-db.netlify.app/panoramas/nn{nn}.jpg",
            f"https://node-db.netlify.app/panoramas/nn{nn}a.jpg",
            f"https://node-db.netlify.app/panoramas/nn{nn}b.jpg",
        ]
        self.assertEqual(saved_panoramas, building.panoramas)

    def test_update_panoramas(self):
        # Fabricate some fake panorama photos
        n = self.install.install_number
        panos = {str(n): PanoramaTitle.from_filenames([f"{n}.jpg", f"{n}a.jpg"])}

        set_panoramas(panos)

        # Now check that that worked.
        building = Building.objects.get(id=self.install.building.id)
        saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
        ]
        self.assertEqual(saved_panoramas, building.panoramas)

        # Now add one from the previous list, and a new one.
        panos = {str(n): PanoramaTitle.from_filenames([f"{n}.jpg", f"{n}b.jpg"])}

        set_panoramas(panos)

        # Now check that that worked. We want all three
        building = Building.objects.get(id=self.install.building.id)
        saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
            f"https://node-db.netlify.app/panoramas/{n}b.jpg",
        ]
        self.assertEqual(saved_panoramas, building.panoramas)


class TestSaveBuildings(TestCase):
    def setUp(self):
        sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        sample_install_copy["building"] = self.building_1

        self.member = Member(**sample_member)
        self.member.save()
        sample_install_copy["member"] = self.member

        self.node = Node(**sample_node)
        self.node.save()
        sample_install_copy["node"] = self.node

        self.install = Install(**sample_install_copy)
        self.install.save()

    def test_save_building_panoramas(self):
        n = self.install.install_number

        # Save some panoramas
        save_building_panoramas(self.building_1, PanoramaTitle.from_filenames([f"{n}.jpg", f"{n}a.jpg"]))
        saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
        ]
        self.assertEqual(saved_panoramas, self.building_1.panoramas)

        # Save another one, and check to make sure it got appended
        save_building_panoramas(self.building_1, PanoramaTitle.from_filenames([f"{n}b.jpg"]))
        saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
            f"https://node-db.netlify.app/panoramas/{n}b.jpg",
        ]
        self.assertEqual(saved_panoramas, self.building_1.panoramas)

        # Save no panoramas, and make sure that none of the panoramas got clobbered.
        save_building_panoramas(self.building_1, [])
        self.assertEqual(saved_panoramas, self.building_1.panoramas)


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
            #  https://github.com/nycmeshnet/meshdb/issues/520

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

    # Crude test to sanity check the API functions
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


class TestRetries(TestCase):
    def setUp(self):
        sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        sample_install_copy["building"] = self.building_1

        self.member = Member(**sample_member)
        self.member.save()
        sample_install_copy["member"] = self.member

        self.node = Node(**sample_node)
        self.node.save()
        sample_install_copy["node"] = self.node

        self.install = Install(**sample_install_copy)
        self.install.save()

        n = self.install.install_number

        # Save some panoramas
        save_building_panoramas(self.building_1, PanoramaTitle.from_filenames([f"{n}.jpg", f"{n}a.jpg"]))
        self.saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
        ]
        self.assertEqual(self.saved_panoramas, self.building_1.panoramas)

    @patch("meshapi.util.panoramas.get_head_tree_sha")
    def test_panorama_retries(self, get_head_tree_sha_function):
        get_head_tree_sha_function.side_effect = GitHubError
        with self.assertRaises(GitHubError):
            panoramas_saved, warnings = sync_github_panoramas()

        self.assertEqual(self.saved_panoramas, self.building_1.panoramas)

    @patch("meshapi.util.panoramas.get_head_tree_sha", return_value="mockedsha")
    @patch("meshapi.util.panoramas.list_files_in_git_directory")
    def test_panorama_retries_2(self, list_files_in_git_directory, _):
        list_files_in_git_directory.side_effect = GitHubError
        with self.assertRaises(GitHubError):
            panoramas_saved, warnings = sync_github_panoramas()

        self.assertEqual(self.saved_panoramas, self.building_1.panoramas)

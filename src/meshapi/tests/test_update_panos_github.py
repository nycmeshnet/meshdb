import os
from django.test import Client, TestCase
from django.contrib.auth.models import User

from meshapi.models import Building, Install, Link, Member, Sector
from meshapi.views import panoramas
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
        panos = {n: [f"{n}.jpg", f"{n}a.jpg"]}

        panoramas.set_panoramas(panos)

        # Now check that that worked.
        building = Building.objects.get(id=self.install.building.id)
        saved_panoramas = [
            f"https://node-db.netlify.app/panoramas/{n}.jpg",
            f"https://node-db.netlify.app/panoramas/{n}a.jpg",
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
    def test_update_panoramas_authenticated(self):
        response = self.admin_c.get("/api/v1/update-panoramas/")
        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )


class TestPanoUtils(TestCase):
    def setUp(self):
        # Check that we have all the environment variables we need
        self.owner = os.environ.get("PANO_REPO_OWNER")
        self.repo = os.environ.get("PANO_REPO")
        self.branch = os.environ.get("PANO_BRANCH")
        self.directory = os.environ.get("PANO_DIR")
        self.host_url = os.environ.get("PANO_HOST")
        self.token = os.environ.get("PANO_GITHUB_TOKEN")

        if (
            not self.owner
            or not self.repo
            or not self.branch
            or not self.directory
            or not self.host_url
            or not self.token
        ):
            raise Exception("Did not find environment variables.")

    def test_parse_pano_title(self):
        test_cases = {
            # Normal cases
            "9035.jpg": ("9035", ""),
            "9035a.jpg": ("9035", "a"),
            # Hypotheticals
            "903590232289437230978078923047589204710578901457891230587abcdefghijklmnopqrstuv.jpg": (
                "903590232289437230978078923047589204710578901457891230587",
                "abcdefghijklmnopqrstuv",
            ),
            "888.jpg.jpg": ("888", ".jpg"),
            # Dumb edge cases
            "IMG_5869.jpg": ("5869", ""),
            " 11001d.jpg": ("11001", "d"),
        }
        for case, expected in test_cases.items():
            result = panoramas.parse_pano_title(case)
            self.assertEqual(result, expected, f"Expected: {expected}. Result: {result}.")

    # The GitHub does not have a perfectly uniform set of files.
    def test_parse_pano_bad_title(self):
        with self.assertRaises(panoramas.BadPanoramaTitle):
            test_cases = {
                "Icon\r": ("", ""),
                "": ("", ""),
                "chom": ("", ""),
            }
            for case, _ in test_cases.items():
                panoramas.parse_pano_title(case)

    # Crude test to sanity check that fn
    # Also this API likes to give me 500s and it would be nice to know if that was
    # a common enough thing to disrupt tests. I guess this is designed to detect
    # flakiness
    def test_github_API(self):
        head_tree_sha = panoramas.get_head_tree_sha(self.owner, self.repo, self.branch)
        assert head_tree_sha is not None

        panorama_files = panoramas.list_files_in_git_directory(self.owner, self.repo, self.directory, head_tree_sha)
        assert panorama_files is not None

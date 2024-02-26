from django.test import Client, TestCase
from django.contrib.auth.models import User

from meshapi.models import Building, Install, Link, Member, Sector
from meshapi.views import panoramas
from .sample_data import sample_building, sample_install, sample_member


class TestFullPanoPipeline(TestCase):
    c = Client()

    def setUp(self):
        sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        sample_install_copy["building"] = self.building_1

        self.building_2 = Building(**sample_building)
        self.building_2.street_address = "69" + str(self.building_2.street_address)
        self.building_2.save()

        self.member = Member(**sample_member)
        self.member.save()
        sample_install_copy["member"] = self.member

        self.install = Install(**sample_install_copy)
        self.install.save()

        self.sector = Sector(
            id=1,
            name="Vernon",
            device_name="LAP-120",
            building=self.building_1,
            status="Active",
            azimuth=0,
            width=120,
            radius=0.3,
        )
        self.sector.save()

        self.link = Link(
            from_building=self.building_1,
            to_building=self.building_2,
            status=Link.LinkStatus.ACTIVE,
        )
        self.link.save()

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")


class TestPanoUtils(TestCase):
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
                "Icon\r": ("",""),
                "": ("",""),
                "chom": ("",""),
            }
            for case, _ in test_cases.items():
                panoramas.parse_pano_title(case)



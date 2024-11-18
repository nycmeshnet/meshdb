from django.contrib.auth.models import User
from django.test import Client, TestCase
from freezegun import freeze_time

from meshapi.models import Building, Install, Member
from meshapi.tests.sample_data import sample_building, sample_install, sample_member


@freeze_time("2024-11-16")
class TestWebsiteStats(TestCase):
    def setUp(self):
        self.sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()

        self.member = Member(**sample_member)
        self.member.save()

        self.install1 = Install(
            **self.sample_install_copy,
            building=self.building_1,
            member=self.member,
        )
        self.install1.status = Install.InstallStatus.REQUEST_RECEIVED
        self.install1.save()

        self.install28 = Install(
            **self.sample_install_copy,
            install_number=28,
            building=self.building_1,
            member=self.member,
        )
        self.install28.save()

    def test_empty_db(self):
        self.install1.delete()
        self.install28.delete()
        svg_response = self.client.get("/website-embeds/stats-graph.svg")
        self.assertContains(svg_response, "No installs found, is the database empty?", status_code=500)

    def test_graph_svg_days_param(self):
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=0")
        self.assertEqual(svg_response.status_code, 200)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=5")
        self.assertEqual(svg_response.status_code, 200)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=7")
        self.assertEqual(svg_response.status_code, 200)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=28")
        self.assertEqual(svg_response.status_code, 200)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=31")
        self.assertEqual(svg_response.status_code, 200)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=300")
        self.assertEqual(svg_response.status_code, 200)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=365")
        self.assertEqual(svg_response.status_code, 200)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=-1")
        self.assertEqual(svg_response.status_code, 400)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=abc")
        self.assertEqual(svg_response.status_code, 400)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=0%2E0")
        self.assertEqual(svg_response.status_code, 400)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=0.0")
        self.assertEqual(svg_response.status_code, 400)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=0.")
        self.assertEqual(svg_response.status_code, 400)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?days=.0")
        self.assertEqual(svg_response.status_code, 400)

    def test_graph_svg_data_param(self):
        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=active_installs")
        self.assertEqual(svg_response.status_code, 200)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=install_requests")
        self.assertEqual(svg_response.status_code, 200)
        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=asdfadsf")
        self.assertEqual(svg_response.status_code, 400)

    def test_graph_svg_looks_roughly_right(self):
        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=active_installs&days=365")
        self.assertEqual(svg_response.status_code, 200)
        self.assertContains(svg_response, "Active Installs")
        self.assertContains(svg_response, ">1</text>")
        self.assertContains(svg_response, ">Nov 17, 2023</text>")
        self.assertContains(svg_response, ">Nov 16, 2024</text>")

        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=install_requests&days=31")
        self.assertEqual(svg_response.status_code, 200)
        self.assertContains(svg_response, "Install Requests")
        self.assertContains(svg_response, ">2</text>")
        self.assertContains(svg_response, ">Oct 16, 2024</text>")
        self.assertContains(svg_response, ">Nov 16, 2024</text>")

from django.test import RequestFactory, TestCase
from freezegun import freeze_time
from parameterized import parameterized

from meshapi.models import Building, Install, Member
from meshapi.tests.sample_data import sample_building, sample_install, sample_member
from meshweb.views import cors_allow_website_stats_to_all


@freeze_time("2024-11-16")
class TestWebsiteStatsGraph(TestCase):
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
        self.assertContains(svg_response, ">1</text>")
        self.assertContains(svg_response, ">Nov 17, 2023</text>")
        self.assertContains(svg_response, ">Nov 16, 2024</text>")

        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=install_requests&days=31")
        self.assertEqual(svg_response.status_code, 200)
        self.assertContains(svg_response, ">2</text>")
        self.assertContains(svg_response, ">Oct 16, 2024</text>")
        self.assertContains(svg_response, ">Nov 16, 2024</text>")


@freeze_time("2024-11-16")
class TestWebsiteStatsJSON(TestCase):
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
        response = self.client.get("/website-embeds/stats-graph.json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": "No installs found, is the database empty?"})

    def test_days_param(self):
        json_response = self.client.get("/website-embeds/stats-graph.json?days=0")
        self.assertEqual(json_response.status_code, 200)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=5")
        self.assertEqual(json_response.status_code, 200)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=7")
        self.assertEqual(json_response.status_code, 200)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=28")
        self.assertEqual(json_response.status_code, 200)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=31")
        self.assertEqual(json_response.status_code, 200)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=300")
        self.assertEqual(json_response.status_code, 200)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=365")
        self.assertEqual(json_response.status_code, 200)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=-1")
        self.assertEqual(json_response.status_code, 400)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=abc")
        self.assertEqual(json_response.status_code, 400)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=0%2E0")
        self.assertEqual(json_response.status_code, 400)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=0.0")
        self.assertEqual(json_response.status_code, 400)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=0.")
        self.assertEqual(json_response.status_code, 400)
        json_response = self.client.get("/website-embeds/stats-graph.json?days=.0")
        self.assertEqual(json_response.status_code, 400)

    def test_data_param(self):
        json_response = self.client.get("/website-embeds/stats-graph.json?data=active_installs")
        self.assertEqual(json_response.status_code, 200)
        json_response = self.client.get("/website-embeds/stats-graph.json?data=install_requests")
        self.assertEqual(json_response.status_code, 200)
        json_response = self.client.get("/website-embeds/stats-graph.json?data=asdfadsf")
        self.assertEqual(json_response.status_code, 400)

    def test_json_data_is_correct(self):
        json_response = self.client.get("/website-embeds/stats-graph.json?data=active_installs&days=365")
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(json_response.json(), {"data": [1] * 100, "start": 1700179200, "end": 1731715200})

        json_response = self.client.get("/website-embeds/stats-graph.json?data=install_requests&days=31")
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(json_response.json(), {"data": [2] * 100, "start": 1729036800, "end": 1731715200})


class TestWebsiteStatsCORS(TestCase):
    @parameterized.expand(
        [
            ["https://nycmesh.net", True],
            ["https://www.nycmesh.net", True],
            ["https://deploy-preview-1--nycmesh-website.netlify.app", True],
            ["https://deploy-preview-11--nycmesh-website.netlify.app", True],
            ["https://deploy-preview-171--nycmesh-website.netlify.app", True],
            ["https://deploy-preview-17111--nycmesh-website.netlify.app", True],
            ["https://bad-guy.netlify.app", False],
        ]
    )
    def test_stats_endpoints_cors(self, origin, expected):
        rf = RequestFactory()

        json_request = rf.post(
            "https://mock-meshdb-url.example/website-embeds/stats-graph.json",
            headers={"Origin": origin},
        )
        self.assertEqual(cors_allow_website_stats_to_all(None, json_request), expected)

        svg_request = rf.post(
            "https://mock-meshdb-url.example/website-embeds/stats-graph.svg",
            headers={"Origin": origin},
        )
        self.assertEqual(cors_allow_website_stats_to_all(None, svg_request), expected)

    def test_other_endpoint_cors(self):
        rf = RequestFactory()

        mock_join_form_request = rf.post(
            "https://mock-meshdb-url.example/aslfkdjdsa",
            headers={"Origin": "https://www.nycmesh.net"},
        )

        self.assertFalse(cors_allow_website_stats_to_all(None, mock_join_form_request))

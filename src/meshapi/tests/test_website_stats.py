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

        # Building
        self.building_1 = Building(**sample_building)
        self.building_1.save()

        # Member
        self.member = Member(**sample_member)
        self.member.save()

        # -----------------Request Received-----------------

        # Install - Status = Request Received, Created before 31 days
        self.install1 = Install(
            **self.sample_install_copy,
            building=self.building_1,
            member=self.member,
        )
        self.install1.status = Install.InstallStatus.REQUEST_RECEIVED
        self.install1.request_date = "2024-10-15T00:00:00Z"
        self.install1.save()

        # Install - Status = Request Received, Created during period
        self.install32 = Install(
            **self.sample_install_copy,
            install_number=32,
            building=self.building_1,
            member=self.member,
        )
        self.install32.status = Install.InstallStatus.REQUEST_RECEIVED
        self.install32.request_date = "2024-11-15T00:00:00Z"
        self.install32.save()

        # Install - Status = Request Received, Created at last day of period
        self.install33 = Install(
            **self.sample_install_copy,
            install_number=33,
            building=self.building_1,
            member=self.member,
        )
        self.install33.status = Install.InstallStatus.REQUEST_RECEIVED
        self.install33.request_date = "2024-11-16T00:00:00Z"
        self.install33.save()

        # Install - Status = Request Received, Created after period
        self.install34 = Install(
            **self.sample_install_copy,
            install_number=34,
            building=self.building_1,
            member=self.member,
        )
        self.install34.status = Install.InstallStatus.REQUEST_RECEIVED
        self.install34.request_date = "2024-11-17T00:00:00Z"
        self.install34.save()

        # ----------------------Active----------------------

        # Install - Status = Active, Created before 365 days
        self.install35 = Install(
            **self.sample_install_copy,
            install_number=35,
            building=self.building_1,
            member=self.member,
        )
        self.install35.install_date = "2023-11-15"
        self.install35.save()

        # Install - Status = Active, Created during period
        self.install36 = Install(
            **self.sample_install_copy,
            install_number=36,
            building=self.building_1,
            member=self.member,
        )
        self.install36.install_date = "2024-11-12"
        self.install36.save()

        # Install - Status = Active, Created at last day of period
        self.install37 = Install(
            **self.sample_install_copy,
            install_number=37,
            building=self.building_1,
            member=self.member,
        )
        self.install37.install_date = "2024-11-16"
        self.install37.save()

        # Install - Status = Active, Created after period
        self.install38 = Install(
            **self.sample_install_copy,
            install_number=38,
            building=self.building_1,
            member=self.member,
        )
        self.install38.install_date = "2024-11-17"
        self.install38.save()

    def test_empty_db(self):
        self.install1.delete()
        self.install32.delete()
        self.install33.delete()
        self.install34.delete()
        self.install35.delete()
        self.install36.delete()
        self.install37.delete()
        self.install38.delete()
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
        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=active_installs&days=0")
        self.assertEqual(svg_response.status_code, 200)

        self.assertContains(svg_response, ">3</text>")
        self.assertContains(svg_response, ">Feb 27, 2022</text>")
        self.assertContains(svg_response, ">Nov 16, 2024</text>")

        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=active_installs&days=365")
        self.assertEqual(svg_response.status_code, 200)

        self.assertContains(svg_response, ">1</text>")
        self.assertContains(svg_response, ">Nov 17, 2023</text>")
        self.assertContains(svg_response, ">Nov 16, 2024</text>")

        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=install_requests&days=0")
        self.assertEqual(svg_response.status_code, 200)

        self.assertContains(svg_response, ">4</text>")
        self.assertContains(svg_response, ">Feb 27, 2022</text>")
        self.assertContains(svg_response, ">Nov 16, 2024</text>")

        svg_response = self.client.get("/website-embeds/stats-graph.svg?data=install_requests&days=31")
        self.assertEqual(svg_response.status_code, 200)

        self.assertContains(svg_response, ">7</text>")
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

from django.contrib.auth.models import User
from django.test import TestCase

from meshapi.models import Install, Building, Member, Node
from meshapi.tests.sample_data import sample_install, sample_building, sample_member, sample_node


class TestDisambiguate(TestCase):
    def setUp(self):
        self.sample_install_copy = sample_install.copy()
        self.building_1 = Building(**sample_building)
        self.building_1.save()
        self.sample_install_copy["building"] = self.building_1

        self.member = Member(**sample_member)
        self.member.save()
        self.sample_install_copy["member"] = self.member

        self.active_install_node = Node(
            **sample_node,
            network_number=201,
            id="6db25b1e-2b43-47f3-8acd-4c540d77b89e",
        )
        self.active_install_node.save()

        self.active_install = Install(
            **self.sample_install_copy,
            id="ca5d22ee-ae54-44b9-9aff-2f6e07a2c4b7",
            install_number=11000,
            node=self.active_install_node,
        )
        self.active_install.save()

        self.active_install_low_number_node = Node(
            **sample_node,
            network_number=100,
            id="472676bb-f07d-443a-8eda-753a2803ef89",
        )
        self.active_install_low_number_node.save()

        self.active_install_low_number_king_of_node = Install(
            **self.sample_install_copy,
            id="2a38c763-e2d0-4edc-93b1-5a5bce23bc49",
            install_number=100,
            node=self.active_install_low_number_node,
        )
        self.active_install_low_number_king_of_node.save()

        self.active_install_low_number_non_king = Install(
            **self.sample_install_copy,
            id="f1a53017-0249-4ccd-aa9e-3497ebb0abbe",
            install_number=150,
            node=self.active_install_low_number_node,
        )
        self.active_install_low_number_non_king.save()

        self.install_no_node = Install(
            **self.sample_install_copy,
            id="5e05afc1-6767-44ae-addd-ce7d1c37bf05",
            install_number=12000,
        )
        self.install_no_node.status = Install.InstallStatus.REQUEST_RECEIVED
        self.install_no_node.save()

        self.recycled_install = Install(
            **self.sample_install_copy,
            id="f9265de3-3d6c-4a36-bd38-f757768e7833",
            install_number=123,
        )
        self.recycled_install.status = Install.InstallStatus.REQUEST_RECEIVED
        self.recycled_install.save()

        self.node_with_recycled_number = Node(
            **sample_node,
            network_number=123,
            id="34f9961b-d0b3-4920-bda9-a08e9a8a6fc1",
        )
        self.node_with_recycled_number.save()

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.client.login(username="admin", password="admin_password")

    def test_disambiguate_unauth(self):
        self.client.logout()
        response = self.client.get("/api/v1/disambiguate-number/?number=201")
        self.assertEqual(
            403,
            response.status_code,
            f"status code incorrect, should be 403, but got {response.status_code}",
        )

    def test_disambiguate_no_number(self):
        response = self.client.get("/api/v1/disambiguate-number/")
        self.assertEqual(
            400,
            response.status_code,
            f"status code incorrect, should be 400, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(),
            {"detail": "Invalid number: ''. Must be an integer greater than zero"},
        )

    def test_disambiguate_negative_number(self):
        response = self.client.get("/api/v1/disambiguate-number/?number=-213")
        self.assertEqual(
            400,
            response.status_code,
            f"status code incorrect, should be 400, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(),
            {"detail": "Invalid number: '-213'. Must be an integer greater than zero"},
        )

    def test_disambiguate_nonexistent_number(self):
        response = self.client.get("/api/v1/disambiguate-number/?number=2137213")
        self.assertEqual(
            404,
            response.status_code,
            f"status code incorrect, should be 404, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(),
            {"detail": "Provided number: 2137213 did not correspond to any install or node objects"},
        )

    def test_disambiguate_active_install(self):
        response = self.client.get("/api/v1/disambiguate-number/?number=11000")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(),
            {
                "resolved_node": {
                    "id": self.active_install_node.id,
                    "network_number": 201,
                },
                "supporting_data": {
                    "exact_match_recycled_install": None,
                    "exact_match_node": None,
                    "exact_match_nonrecycled_install": {
                        "id": self.active_install.id,
                        "install_number": 11000,
                        "node": {
                            "id": self.active_install_node.id,
                            "network_number": 201,
                        },
                    },
                },
            },
        )

    def test_disambiguate_install_no_node(self):
        response = self.client.get("/api/v1/disambiguate-number/?number=12000")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(),
            {
                "resolved_node": None,
                "supporting_data": {
                    "exact_match_recycled_install": None,
                    "exact_match_node": None,
                    "exact_match_nonrecycled_install": {
                        "id": self.install_no_node.id,
                        "install_number": 12000,
                        "node": None,
                    },
                },
            },
        )

    def test_disambiguate_recyled_install(self):
        response = self.client.get("/api/v1/disambiguate-number/?number=123")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(),
            {
                "resolved_node": {
                    "id": self.node_with_recycled_number.id,
                    "network_number": 123,
                },
                "supporting_data": {
                    "exact_match_recycled_install": {
                        "id": self.recycled_install.id,
                        "install_number": 123,
                        "node": None,
                    },
                    "exact_match_node": {
                        "id": self.node_with_recycled_number.id,
                        "network_number": 123,
                    },
                    "exact_match_nonrecycled_install": None,
                },
            },
        )

    def test_disambiguate_non_recycled_node(self):
        response = self.client.get("/api/v1/disambiguate-number/?number=201")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(),
            {
                "resolved_node": {
                    "id": self.active_install_node.id,
                    "network_number": 201,
                },
                "supporting_data": {
                    "exact_match_recycled_install": None,
                    "exact_match_node": {
                        "id": self.active_install_node.id,
                        "network_number": 201,
                    },
                    "exact_match_nonrecycled_install": None,
                },
            },
        )

    def test_disambiguate_old_active_install_node_combo(self):
        response = self.client.get("/api/v1/disambiguate-number/?number=100")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(),
            {
                "resolved_node": {
                    "id": self.active_install_low_number_node.id,
                    "network_number": 100,
                },
                "supporting_data": {
                    "exact_match_recycled_install": None,
                    "exact_match_node": {
                        "id": self.active_install_low_number_node.id,
                        "network_number": 100,
                    },
                    "exact_match_nonrecycled_install": {
                        "id": self.active_install_low_number_king_of_node.id,
                        "install_number": 100,
                        "node": {
                            "id": self.active_install_low_number_node.id,
                            "network_number": 100,
                        },
                    },
                },
            },
        )

    def test_disambiguate_old_active_install_without_node_combo(self):
        response = self.client.get("/api/v1/disambiguate-number/?number=150")
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(),
            {
                "resolved_node": {
                    "id": self.active_install_low_number_node.id,
                    "network_number": 100,
                },
                "supporting_data": {
                    "exact_match_recycled_install": None,
                    "exact_match_node": None,
                    "exact_match_nonrecycled_install": {
                        "id": self.active_install_low_number_non_king.id,
                        "install_number": 150,
                        "node": {
                            "id": self.active_install_low_number_node.id,
                            "network_number": 100,
                        },
                    },
                },
            },
        )

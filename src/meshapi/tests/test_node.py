import json
import uuid

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from ..models import Building, Install, Member, Node
from .sample_data import sample_building, sample_install, sample_member, sample_node


class TestNodeModel(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.client.login(username="admin", password="admin_password")

        self.sample_node = sample_node.copy()
        self.sample_node["status"] = Node.NodeStatus.PLANNED

    def test_construct_planned_node_no_id_no_network_number_and_update(self):
        node = Node(**self.sample_node)
        node.save()

        self.assertIsNotNone(node.id)
        self.assertIsNone(node.network_number)

        id1 = node.id
        node.notes = "fooo"
        node.save()

        node.refresh_from_db()
        self.assertEqual(node.id, id1)
        self.assertIsNone(node.network_number)

    def test_construct_active_node_no_id_no_network_number_and_update(self):
        active_node_data = self.sample_node.copy()
        active_node_data["status"] = Node.NodeStatus.ACTIVE
        node2 = Node(**active_node_data)
        node2.save()

        self.assertIsNotNone(node2.id)
        self.assertIsNotNone(node2.network_number)
        self.assertGreater(node2.network_number, 0)

        id2 = node2.id
        nn = node2.network_number
        node2.notes = "fooo"
        node2.save()

        node2.refresh_from_db()
        self.assertEqual(node2.id, id2)
        self.assertEqual(node2.network_number, nn)

    def test_construct_planned_node_no_id_yes_network_number(self):
        node = Node(**self.sample_node, network_number=45)
        node.save()

        self.assertIsNotNone(node.id)
        self.assertEqual(node.network_number, 45)

        node2 = Node(**self.sample_node)
        node2.network_number = 89
        node2.save()

        self.assertIsNotNone(node2.id)
        self.assertEqual(node2.network_number, 89)

    def test_construct_active_node_no_id_yes_network_number(self):
        active_node_data = self.sample_node.copy()
        active_node_data["status"] = Node.NodeStatus.ACTIVE
        node = Node(**active_node_data, network_number=45)
        node.save()

        self.assertIsNotNone(node.id)
        self.assertEqual(node.network_number, 45)

        node2 = Node(**active_node_data)
        node2.network_number = 89
        node2.save()

        self.assertIsNotNone(node2.id)
        self.assertEqual(node2.network_number, 89)

    def test_construct_node_with_network_number_stolen_from_active_install(self):
        building = Building(**sample_building)
        building.save()

        member = Member(**sample_member)
        member.save()

        victim_install = Install(
            **sample_install,
            install_number=45,
            building=building,
            member=member,
        )
        victim_install.save()

        active_node_data = self.sample_node.copy()
        active_node_data["status"] = Node.NodeStatus.ACTIVE
        node = Node(**active_node_data, network_number=45)

        with pytest.raises(ValidationError):
            node.save()

        victim_install.refresh_from_db()

        self.assertIsNone(Node.objects.filter(network_number=45).first())
        self.assertEqual(victim_install.status, Install.InstallStatus.ACTIVE)
        self.assertEqual(victim_install.install_number, 45)

    def test_construct_node_with_network_number_stolen_from_inactive_install(self):
        building = Building(**sample_building)
        building.save()

        member = Member(**sample_member)
        member.save()

        victim_install = Install(
            **sample_install,
            install_number=45,
            building=building,
            member=member,
        )
        victim_install.status = Install.InstallStatus.REQUEST_RECEIVED
        victim_install.save()

        active_node_data = self.sample_node.copy()
        active_node_data["status"] = Node.NodeStatus.ACTIVE
        active_node_data["notes"] = "Test node"
        node = Node(**active_node_data, network_number=45)
        node.save()

        node.refresh_from_db()
        victim_install.refresh_from_db()

        self.assertEqual(node.network_number, 45)
        self.assertEqual(node.notes, "Test node")
        self.assertEqual(victim_install.status, Install.InstallStatus.NN_REASSIGNED)
        self.assertEqual(victim_install.install_number, 45)

        node.notes = "fooo"
        node.save()

        self.assertEqual(node.network_number, 45)
        self.assertEqual(node.notes, "fooo")
        self.assertEqual(victim_install.status, Install.InstallStatus.NN_REASSIGNED)
        self.assertEqual(victim_install.install_number, 45)

        # Edit the status so we can confirm the node2.save() below doesn't touch it
        victim_install.status = Install.InstallStatus.CLOSED
        victim_install.save()

        # Trying to steal it a second time should fail without modifying the Install object,
        # it is already in use
        active_node_data = self.sample_node.copy()
        active_node_data["status"] = Node.NodeStatus.ACTIVE
        active_node_data["notes"] = "Test node"
        node2 = Node(**active_node_data, network_number=45)
        with pytest.raises(ValidationError):
            node2.save()

        node45 = Node.objects.get(network_number=45)

        self.assertEqual(node, node45)
        self.assertEqual(victim_install.status, Install.InstallStatus.CLOSED)
        self.assertEqual(victim_install.install_number, 45)

    def test_construct_planned_node_yes_id_no_network_number(self):
        node = Node(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            **self.sample_node,
        )
        node.save()

        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertIsNone(node.network_number)

    def test_construct_active_node_yes_id_no_network_number(self):
        active_node_data = self.sample_node.copy()
        active_node_data["status"] = Node.NodeStatus.ACTIVE
        node = Node(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            **active_node_data,
        )
        node.save()

        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertIsNotNone(node.network_number)

    def test_construct_node_yes_id_yes_network_number(self):
        node = Node(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            network_number=45,
            **self.sample_node,
        )
        node.save()

        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(node.network_number, 45)

    def test_update_planned_node_with_network_number(self):
        node = Node(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            **self.sample_node,
        )
        node.save()

        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertIsNone(node.network_number)

        node.network_number = 78
        node.save()

        node.refresh_from_db()
        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(node.network_number, 78)

    def test_update_planned_node_status_causes_network_number_assignment_and_its_sticky(self):
        node = Node(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            **self.sample_node,
        )
        node.save()

        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertIsNone(node.network_number)

        node.status = Node.NodeStatus.INACTIVE
        node.save()

        node.refresh_from_db()
        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertIsNone(node.network_number)

        node.status = Node.NodeStatus.ACTIVE
        node.save()

        node.refresh_from_db()
        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertIsNotNone(node.network_number)

        node.status = Node.NodeStatus.INACTIVE
        node.save()

        node.refresh_from_db()
        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertIsNotNone(node.network_number)

    def test_update_node_unset_network_number(self):
        node = Node(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            network_number=45,
            **self.sample_node,
        )
        node.save()

        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(node.network_number, 45)

        node.network_number = None
        with pytest.raises(ValidationError):
            node.save()

        node.refresh_from_db()
        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(node.network_number, 45)

    def test_update_node_change_node_number(self):
        node = Node(
            id=uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"),
            network_number=45,
            **self.sample_node,
        )
        node.save()

        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(node.network_number, 45)

        with pytest.raises(ValidationError):
            node.network_number = 78
            node.save()

        node.refresh_from_db()
        self.assertEqual(node.id, uuid.UUID("23ef170c-f37d-44e3-aaac-93dae636c86e"))
        self.assertEqual(node.network_number, 45)

    def test_node_str(self):
        node_data = self.sample_node.copy()
        node_data["status"] = Node.NodeStatus.PLANNED
        node_data["name"] = None
        node = Node(**node_data)
        node.save()

        self.assertEqual(f"Node ID {node.id}", str(node))

        node.name = "Test Node"
        self.assertEqual("Test Node", str(node))

        node.network_number = 45
        self.assertEqual("NN45 (Test Node)", str(node))

        node.name = None
        self.assertEqual("NN45", str(node))


class TestNodeAPI(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.node1 = Node(**sample_node, network_number=101)
        self.node1.save()

        self.node128 = Node(**sample_node, network_number=128)
        self.node128.save()

    def test_new_node(self):
        response = self.c.post(
            "/api/v1/nodes/",
            {
                "network_number": 123,
                "latitude": 0,
                "longitude": 0,
                "status": "Active",
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 123)

        response = self.c.post(
            "/api/v1/nodes/",
            {
                "network_number": None,
                "latitude": 0,
                "longitude": 0,
                "status": "Active",
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
        self.assertEqual(response_obj["network_number"], 102)

    def test_new_node_with_blank_nn_respects_taken_nns(self):
        node2 = Node(network_number=103, **sample_node)
        node2.save()

        response = self.c.post(
            "/api/v1/nodes/",
            {
                "latitude": 0,
                "longitude": 0,
                "status": "Active",
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 102)

        response = self.c.post(
            "/api/v1/nodes/",
            {
                "latitude": 0,
                "longitude": 0,
                "status": "Active",
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 104)

    def test_broken_node(self):
        response = self.c.post(
            "/api/v1/nodes/",
            {
                "network_number": 123,
                "latitude": 0,
                "longitude": 0,
                # Missing status
            },
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_steal_taken_nn(self):
        response = self.c.post(
            "/api/v1/nodes/",
            {
                "network_number": 101,
                "latitude": 0,
                "longitude": 0,
                "status": "Active",
            },
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], ["node with this network number already exists."])
        self.assertEqual(len(Node.objects.all()), 2)

    def test_get_node_by_id(self):
        response = self.c.get(f"/api/v1/nodes/{self.node1.id}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["name"], "Amazing Node")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], None)

    def test_get_node_by_nn(self):
        response = self.c.get(f"/api/v1/nodes/{self.node1.network_number}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["name"], "Amazing Node")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], None)

    def test_modify_node_by_id(self):
        response = self.c.patch(
            f"/api/v1/nodes/{self.node1.id}/",
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
        self.assertEqual(response_obj["name"], "Amazing Node")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], "New notes! Wheee")

    def test_modify_node_by_nn(self):
        response = self.c.patch(
            f"/api/v1/nodes/{self.node1.network_number}/",
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
        self.assertEqual(response_obj["name"], "Amazing Node")
        self.assertEqual(response_obj["status"], "Active")
        self.assertEqual(response_obj["notes"], "New notes! Wheee")

    def test_cant_modify_existing_node_nn(self):
        response = self.c.patch(
            f"/api/v1/nodes/{self.node128.id}/",
            {"network_number": 123},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 128)
        self.node128.refresh_from_db()
        self.assertEqual(self.node128.network_number, 128)

        response = self.c.patch(
            f"/api/v1/nodes/{self.node128.id}/",
            {"network_number": None},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 128)
        self.node128.refresh_from_db()
        self.assertEqual(self.node128.network_number, 128)

    def test_cant_remove_existing_node_nn(self):
        response = self.c.put(
            f"/api/v1/nodes/{self.node128.id}/",
            sample_node,
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )
        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["network_number"], 128)
        self.node128.refresh_from_db()
        self.assertEqual(self.node128.network_number, 128)

    def test_delete_node_by_id(self):
        network_num = self.node1.network_number
        response = self.c.delete(f"/api/v1/nodes/{self.node1.id}/")

        code = 204
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        self.assertEqual(0, len(Node.objects.filter(network_number=network_num)))

    def test_delete_node_by_nn(self):
        network_num = self.node1.network_number
        response = self.c.delete(f"/api/v1/nodes/{self.node1.network_number}/")

        code = 204
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        self.assertEqual(0, len(Node.objects.filter(network_number=network_num)))

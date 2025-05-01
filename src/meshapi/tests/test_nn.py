import datetime
import json
import time
from functools import partial
from unittest import mock
from unittest.mock import patch

from django.conf import os
from django.contrib.auth.models import User
from django.test import Client, TestCase, TransactionTestCase
from parameterized import parameterized

from meshapi.models import Building, Install, Member, Node

from .group_helpers import create_groups
from .sample_data import sample_building, sample_install, sample_member
from .util import TestThread
from django.conf import settings

# Test basic NN form stuff (input validation, etc)
class TestNN(TestCase):
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # Create sample data
        member_obj = Member(**sample_member)
        member_obj.save()

        self.building = Building(**sample_building)
        self.building.latitude = 4
        self.building.longitude = 4
        self.building.save()

        inst = sample_install.copy()
        inst["status"] = Install.InstallStatus.REQUEST_RECEIVED
        if inst["abandon_date"] == "":
            inst["abandon_date"] = None

        inst["building"] = self.building
        inst["member"] = member_obj

        self.install = Install(**inst)
        self.install.install_number = 10001
        self.install.save()

        self.install_number = self.install.install_number

        self.install_obj_low = Install(**inst)
        self.install_obj_low.install_number = 1234
        self.install_obj_low.save()

        self.install_number_low = self.install_obj_low.install_number

    def test_nn_valid_install_number(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = 101
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        node_object = Node.objects.get(network_number=expected_nn)
        self.assertEqual(node_object.status, Node.NodeStatus.PLANNED)
        self.assertEqual(node_object.latitude, self.building.latitude)
        self.assertEqual(node_object.longitude, self.building.longitude)
        self.assertEqual(node_object.install_date, datetime.date.today())

        self.install.refresh_from_db()
        self.assertEqual(self.install.node, node_object)
        self.assertEqual(self.install.status, Install.InstallStatus.PENDING)

        # Now test to make sure that we get 200 for dupes
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number DUPLICATE. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

    def test_doesnt_change_the_status_of_active_nodes(self):
        self.install.status = Install.InstallStatus.ACTIVE
        self.install.save()

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        self.install.refresh_from_db()
        self.assertEqual(self.install.status, Install.InstallStatus.ACTIVE)

    def test_building_already_has_nn(self):
        node = Node(
            network_number=9999,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node.save()

        self.building.primary_node = node
        self.building.save()

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = 9999
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        self.install.refresh_from_db()
        self.assertEqual(self.install.node, node)
        self.assertEqual(self.install.status, Install.InstallStatus.PENDING)
        self.assertEqual(node.status, Node.NodeStatus.ACTIVE)

    def test_node_already_exists_no_nn(self):
        node = Node(
            status=Node.NodeStatus.PLANNED,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node.save()

        node.refresh_from_db()
        self.assertIsNone(node.network_number)

        self.install.node = node
        self.install.save()

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        node.refresh_from_db()
        self.assertIsNotNone(node.network_number)
        self.assertEqual(node.status, Node.NodeStatus.PLANNED)

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = node.network_number
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        self.install.refresh_from_db()
        self.assertEqual(self.install.node, node)
        self.assertEqual(self.install.status, Install.InstallStatus.PENDING)
        self.building.refresh_from_db()
        self.assertEqual(self.building.primary_node, node)

    def test_node_already_exists_inactive_no_nn(self):
        node = Node(
            status=Node.NodeStatus.INACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node.save()

        node.refresh_from_db()

        self.assertIsNone(node.network_number)

        self.install.node = node
        self.install.save()

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        node.refresh_from_db()
        self.assertIsNotNone(node.network_number)
        self.assertEqual(node.status, Node.NodeStatus.PLANNED)

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = node.network_number
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        self.install.refresh_from_db()
        self.assertEqual(self.install.node, node)
        self.assertEqual(self.install.status, Install.InstallStatus.PENDING)
        self.building.refresh_from_db()
        self.assertEqual(self.building.primary_node, node)

    def test_node_already_exists_on_building_no_nn(self):
        node = Node(
            status=Node.NodeStatus.PLANNED,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node.save()

        node.refresh_from_db()

        self.building.primary_node = node
        self.building.save()

        self.assertIsNone(node.network_number)
        self.assertEqual(node.status, Node.NodeStatus.PLANNED)

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        node.refresh_from_db()
        self.assertIsNotNone(node.network_number)
        self.assertEqual(node.status, Node.NodeStatus.PLANNED)

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = node.network_number
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        self.install.refresh_from_db()
        self.assertEqual(self.install.node, node)
        self.assertEqual(self.install.status, Install.InstallStatus.PENDING)
        self.building.refresh_from_db()
        self.assertEqual(self.building.primary_node, node)

    def test_node_already_exists_on_building_and_install_no_nn(self):
        node = Node(
            status=Node.NodeStatus.PLANNED,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node.save()

        node.refresh_from_db()

        self.building.primary_node = node
        self.building.save()

        self.install.node = node
        self.install.save()

        self.assertIsNone(node.network_number)

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        node.refresh_from_db()
        self.assertIsNotNone(node.network_number)
        self.assertEqual(node.status, Node.NodeStatus.PLANNED)

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = node.network_number
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        self.install.refresh_from_db()
        self.assertEqual(self.install.node, node)
        self.assertEqual(self.install.status, Install.InstallStatus.PENDING)
        self.building.refresh_from_db()
        self.assertEqual(self.building.primary_node, node)

    @patch("meshapi.views.forms.get_next_available_network_number")
    def test_next_nn_failure(self, mock_get_next_nn):
        mock_get_next_nn.side_effect = ValueError("Test failure")

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 500
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        self.assertEqual("NN Request failed. Test failure", json.loads(response.content.decode("utf-8"))["detail"])
        self.assertEqual(0, len(Node.objects.all()))

    def test_nn_valid_low_install_number_unused_nn(self):
        # Check that install numbers that are valid network numbers (i.e. >10 <8192) are used
        # as the network number at assignment time, if there is no existing Node with that NN

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number_low, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = self.install_number_low
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        node_object = Node.objects.get(network_number=expected_nn)
        self.install_obj_low.refresh_from_db()
        self.assertEqual(self.install_obj_low.node, node_object)
        self.assertEqual(node_object.status, Node.NodeStatus.PLANNED)
        self.assertEqual(self.install_obj_low.status, Install.InstallStatus.PENDING)

    def test_nn_valid_low_install_number_used_nn(self):
        # Check that install numbers that are valid network numbers (i.e. >10 <8192) are NOT used
        # as the network number at assignment time, if there is an existing Node with that NN

        node = Node(
            network_number=self.install_number_low,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node.save()

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number_low, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = 101
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        node_object = Node.objects.get(network_number=expected_nn)
        self.install_obj_low.refresh_from_db()
        self.assertEqual(self.install_obj_low.node, node_object)
        self.assertEqual(node_object.status, Node.NodeStatus.PLANNED)

    @parameterized.expand(
        [
            Install.InstallStatus.NN_REASSIGNED,
            Install.InstallStatus.CLOSED,
        ]
    )
    def test_nn_valid_low_install_number_reassigned_but_unused_nn(self, status_to_eval):
        # Check that install numbers that are valid network numbers (i.e. >10 <8192) are NOT used
        # as the network number at assignment time, if the status on the install indicates
        # that it potentially has been used elsewhere, even if there isn't an existing Node with that NN

        self.install_obj_low.status = status_to_eval
        self.install_obj_low.save()

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number_low, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = 101
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        node_object = Node.objects.get(network_number=expected_nn)
        self.install_obj_low.refresh_from_db()
        self.assertEqual(self.install_obj_low.node, node_object)
        self.assertEqual(node_object.status, Node.NodeStatus.PLANNED)

    @parameterized.expand(
        [
            Install.InstallStatus.INACTIVE,
            Install.InstallStatus.PENDING,
            Install.InstallStatus.BLOCKED,
        ]
    )
    def test_nn_valid_low_install_status_changed_but_unused_nn(self, status_to_eval):
        # Check that install numbers that are valid network numbers (i.e. >10 <8192) are used
        # as the network number at assignment time, if the status on the install has been changed
        # from the default, but to something that doesn't indicate NN reservation or re-use

        self.install_obj_low.status = status_to_eval
        self.install_obj_low.save()

        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number_low, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

        resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
        expected_nn = self.install_number_low
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        node_object = Node.objects.get(network_number=expected_nn)
        self.install_obj_low.refresh_from_db()
        self.assertEqual(self.install_obj_low.node, node_object)
        self.assertEqual(node_object.status, Node.NodeStatus.PLANNED)

    def test_nn_invalid_password(self):
        unauth_client = Client()
        response = unauth_client.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number, "password": "chom"},
            content_type="application/json",
        )

        code = 403
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

    def test_nn_no_password_admin(self):
        installer_client = Client()
        installer = User.objects.create_superuser(
            username="installer", password="installer_password", email="admin@example.com"
        )
        _, installer_group, _ = create_groups()
        installer.groups.add(installer_group)
        installer_client.login(username="installer", password="installer_password")

        response = installer_client.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

    def test_nn_no_password_installer(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": self.install_number},
            content_type="application/json",
        )

        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response.status_code}",
        )

    def test_nn_invalid_building_id(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": 69420, "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 404
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_invalid_building_id. Should be {code}, but got {response.status_code}",
        )

    def test_nn_bad_request(self):
        response = self.admin_c.post(
            "/api/v1/nn-assign/",
            {"install_number": "chom", "password": settings.NN_ASSIGN_PSK},
            content_type="application/json",
        )

        code = 404
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_invalid_building_id. Should be {code}, but got {response.status_code}",
        )

        response = self.admin_c.post("/api/v1/nn-assign/", "Tell me your secrets >:)", content_type="application/json")

        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect for test_nn_invalid_building_id. Should be {code}, but got {response.status_code}",
        )


# Test that the NN function can find gaps
class TestFindGaps(TestCase):
    c = Client()
    admin_c = Client()

    def add_data(self, b, m, i, index=101, create_node=False):
        i = i.copy()
        b["zip_code"] = str(int(b["zip_code"]) + index)
        b["address_truth_sources"] = ["NYCPlanningLabs"]
        if i["abandon_date"] == "":
            i["abandon_date"] = None

        building_obj = Building(**b)
        i["building"] = building_obj

        m["primary_email_address"] = f"john{index}@gmail.com"
        member_obj = Member(**m)
        i["member"] = member_obj
        i["ticket_number"] = index
        install_obj = Install(**i, install_number=index)

        if create_node:
            node = Node(
                network_number=index,
                status=Node.NodeStatus.ACTIVE,
                latitude=0,
                longitude=0,
            )
            node.save()

            building_obj.primary_node = node
            install_obj.node = node

        member_obj.save()
        building_obj.save()
        install_obj.save()

        i["install_number"] = install_obj.install_number

        return i

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # Create a whole bunch of sample data
        build = sample_building.copy()
        inst = sample_install.copy()
        memb = sample_member.copy()
        build["street_address"] = "123 Fake St"
        for i in range(101, 111):
            self.add_data(build, memb, inst, index=i, create_node=True)

        # Skip a few numbers (111, 112)
        for i in range(113, 130):
            self.add_data(build, memb, inst, index=i, create_node=True)

        # Inactive install, reserves the install number as an NN even though
        # no NN is technically assigned
        inst["status"] = Install.InstallStatus.INACTIVE
        self.add_data(build, memb, inst, index=130, create_node=False)

        # Old join request, doesn't reserve the NN
        inst["status"] = Install.InstallStatus.REQUEST_RECEIVED
        self.add_data(build, memb, inst, index=131, create_node=False)

        # Then create another couple installs
        # These will get numbers assigned next
        b2 = sample_building.copy()
        m2 = sample_member.copy()
        self.inst2 = sample_install.copy()
        self.inst2 = self.add_data(b2, m2, self.inst2, index=50002, create_node=False)

        b3 = sample_building.copy()
        m3 = sample_member.copy()
        self.inst3 = sample_install.copy()
        self.inst3 = self.add_data(b3, m3, self.inst3, index=50003, create_node=False)

        b4 = sample_building.copy()
        m4 = sample_member.copy()
        self.inst4 = sample_install.copy()
        self.inst4 = self.add_data(b4, m4, self.inst4, index=50004, create_node=False)

    def test_nn_search_for_new_number(self):
        # Try to give NNs to all the installs. Should end up with two right
        # next to each other and then one at the end.

        for inst, nn in [(self.inst2, 111), (self.inst3, 112), (self.inst4, 131)]:
            response = self.admin_c.post(
                "/api/v1/nn-assign/",
                {"install_number": inst["install_number"], "password": settings.NN_ASSIGN_PSK},
                content_type="application/json",
            )
            response.content.decode("utf-8")

            code = 201
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for test_nn_valid_building_id. Should be {code}, but got {response.status_code}",
            )

            resp_nn = json.loads(response.content.decode("utf-8"))["network_number"]
            expected_nn = nn

            self.assertEqual(
                resp_nn,
                expected_nn,
                f"Got wrong nn for install {inst['install_number']}. Got {resp_nn} but expected {expected_nn}",
            )

        # Sanity check that the other buildings actually exist
        self.assertIsNotNone(Install.objects.filter(node__network_number=129)[0].install_number)
        self.assertIsNotNone(Building.objects.filter(primary_node__network_number=129)[0].id)

        self.assertIsNotNone(Install.objects.filter(node__network_number=131)[0].install_number)
        self.assertIsNotNone(Building.objects.filter(primary_node__network_number=131)[0].id)


class TestNNRaceCondition(TransactionTestCase):
    admin_c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.admin_c.login(username="admin", password="admin_password")

        # Create sample data
        member_obj = Member(**sample_member)
        member_obj.save()

        building = sample_building.copy()
        building_obj1 = Building(**building)
        building_obj1.save()

        building_obj2 = Building(**building)
        building_obj2.save()

        building_obj3 = Building(**building)
        building_obj3.save()

        inst = sample_install.copy()

        if inst["abandon_date"] == "":
            inst["abandon_date"] = None

        inst["building"] = building_obj1
        inst["member"] = member_obj
        inst["status"] = Install.InstallStatus.REQUEST_RECEIVED

        install_obj1 = Install(**inst)
        install_obj1.install_number = 10001
        install_obj1.save()

        inst["building"] = building_obj2

        install_obj2 = Install(**inst)
        install_obj2.install_number = 10002
        install_obj2.save()

        # Unused, just to add something else to the DB to check edge cases
        inst["building"] = building_obj3
        install_obj3 = Install(**inst)
        install_obj3.install_number = 10003
        install_obj3.save()

        self.install_number1 = install_obj1.install_number
        self.install_number2 = install_obj2.install_number

    def test_different_installs_race_condition(self):
        outputs_dict = {}

        def invoke_nn_form(install_num: int, outputs_dict: dict):
            # Slow down the call which looks up the NN to force the race condition
            with mock.patch("meshapi.util.network_number.no_op", partial(time.sleep, 1)):
                result = self.admin_c.post(
                    "/api/v1/nn-assign/",
                    {"install_number": install_num, "password": settings.NN_ASSIGN_PSK},
                    content_type="application/json",
                )
                outputs_dict[install_num] = result

        t1 = TestThread(target=invoke_nn_form, args=(self.install_number1, outputs_dict))
        t2 = TestThread(target=invoke_nn_form, args=(self.install_number2, outputs_dict))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        response1 = outputs_dict[self.install_number1]
        response2 = outputs_dict[self.install_number2]

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response1.status_code}",
        )

        resp_nns = {
            json.loads(response1.content.decode("utf-8"))["network_number"],
            json.loads(response2.content.decode("utf-8"))["network_number"],
        }
        expected_nns = {101, 102}
        self.assertEqual(
            expected_nns,
            resp_nns,
            f"NNs incorrect for test_nn_valid_install_number. Should be {expected_nns}, but got {resp_nns}",
        )

        code = 201
        self.assertEqual(
            code,
            response2.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response2.status_code}",
        )

    def test_save_and_form_race_condition(self):
        outputs_dict = {}

        def invoke_nn_form(install_num: int, outputs_dict: dict):
            # Slow down the call which looks up the NN to force the race condition
            with mock.patch("meshapi.util.network_number.no_op", partial(time.sleep, 1)):
                result = self.admin_c.post(
                    "/api/v1/nn-assign/",
                    {"install_number": install_num, "password": settings.NN_ASSIGN_PSK},
                    content_type="application/json",
                )
                outputs_dict[install_num] = result

        def invoke_nn_lookup_from_save(outputs_dict: dict):
            try:
                # Slow down the call which looks up the NN to force the race condition
                with mock.patch("meshapi.util.network_number.no_op", partial(time.sleep, 1)):
                    node = Node(
                        status=Node.NodeStatus.ACTIVE,
                        type=Node.NodeType.STANDARD,
                        latitude=0,
                        longitude=0,
                    )
                    # This save() should cause a call to get_next_available_network_number()
                    # in order to determine the primary key prior to DB write, but since we slowed it
                    # down, a race condition will occur unless the save() func properly protects the call
                    node.save()
                    node.refresh_from_db()
                    outputs_dict["save_call"] = node.network_number
            except Exception as e:
                outputs_dict["save_call"] = e

        t1 = TestThread(target=invoke_nn_form, args=(self.install_number1, outputs_dict))
        t2 = TestThread(target=invoke_nn_lookup_from_save, args=(outputs_dict,))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        response1 = outputs_dict[self.install_number1]

        # Re-raise the exception from the .save() call to fail the test if needed
        # (.join() does not do this propagation automatically)
        if isinstance(outputs_dict["save_call"], Exception):
            raise ValueError() from outputs_dict[outputs_dict["save_call"]]

        code = 201
        self.assertEqual(
            code,
            response1.status_code,
            f"status code incorrect for test_nn_valid_install_number. Should be {code}, but got {response1.status_code}",
        )

        resp_nns = {
            json.loads(response1.content.decode("utf-8"))["network_number"],
            outputs_dict["save_call"],
        }
        expected_nns = {101, 102}
        self.assertEqual(
            expected_nns,
            resp_nns,
            f"NNs incorrect for test_nn_valid_install_number. Should be {expected_nns}, but got {resp_nns}",
        )

    def test_same_install_race_condition(self):
        outputs = []

        def invoke_nn_form(install_num: int, outputs: list):
            # Slow down the call which looks up the NN to force the race condition
            with mock.patch("meshapi.util.network_number.no_op", partial(time.sleep, 1)):
                result = self.admin_c.post(
                    "/api/v1/nn-assign/",
                    {"install_number": install_num, "password": settings.NN_ASSIGN_PSK},
                    content_type="application/json",
                )
                outputs.append(result)

        t1 = TestThread(target=invoke_nn_form, args=(self.install_number1, outputs))
        t2 = TestThread(target=invoke_nn_form, args=(self.install_number1, outputs))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        response1 = outputs[0]
        response2 = outputs[1]

        expected_codes = {201, 200}
        received_codes = {response1.status_code, response2.status_code}
        self.assertEqual(
            expected_codes,
            received_codes,
            f"status codes incorrect for test_nn_valid_install_number. Should be {expected_codes}, but got {received_codes}",
        )

        resp_nn = json.loads(response1.content.decode("utf-8"))["network_number"]
        expected_nn = 101
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

        resp_nn = json.loads(response2.content.decode("utf-8"))["network_number"]
        expected_nn = 101
        self.assertEqual(
            expected_nn,
            resp_nn,
            f"nn incorrect for test_nn_valid_install_number. Should be {expected_nn}, but got {resp_nn}",
        )

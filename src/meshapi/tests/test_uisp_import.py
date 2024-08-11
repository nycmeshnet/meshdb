import datetime
from unittest.mock import call, patch

import pytest
from dateutil.tz import tzutc
from django.test import TestCase

from meshapi.models import LOS, Building, Device, Link, Node
from meshapi.serializers import DeviceSerializer
from meshapi.util.uisp_import.handler import (
    import_and_sync_uisp_devices,
    import_and_sync_uisp_links,
    sync_link_table_into_los_objects,
)
from meshapi.util.uisp_import.update_objects import update_device_from_uisp_data, update_link_from_uisp_data
from meshapi.util.uisp_import.utils import (
    get_building_from_network_number,
    get_link_type,
    get_uisp_link_last_seen,
    notify_admins_of_changes,
    parse_uisp_datetime,
)


class TestUISPImportUtils(TestCase):
    def test_parse_uisp_datetime(self):
        self.assertEqual(
            parse_uisp_datetime("2018-11-14T15:20:32.004Z"),
            datetime.datetime(2018, 11, 14, 15, 20, 32, 4000, tzinfo=tzutc()),
        )

    def test_get_link_type(self):
        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": None}),  # Default to 5 GHz
            Link.LinkType.FIVE_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 5000}),
            Link.LinkType.FIVE_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 5900}),
            Link.LinkType.FIVE_GHZ,
        )

        self.assertEqual(
            # TODO: Once 6 GHz becomes a thing, this will probably need to be tweaked
            #  for now we consider anything < 7 GHz as 5 GHz
            get_link_type({"type": "wireless", "frequency": 6100}),
            Link.LinkType.FIVE_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 24000}),
            Link.LinkType.TWENTYFOUR_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 23000}),
            Link.LinkType.TWENTYFOUR_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 25000}),
            Link.LinkType.TWENTYFOUR_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 60000}),
            Link.LinkType.SIXTY_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 61000}),
            Link.LinkType.SIXTY_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 59000}),
            Link.LinkType.SIXTY_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 72000}),
            Link.LinkType.SEVENTY_EIGHTY_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 79000}),
            Link.LinkType.SEVENTY_EIGHTY_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "wireless", "frequency": 84000}),
            Link.LinkType.SEVENTY_EIGHTY_GHZ,
        )

        self.assertEqual(
            get_link_type({"type": "ethernet", "frequency": None}),
            Link.LinkType.ETHERNET,
        )

        self.assertEqual(
            get_link_type({"type": "ethernet", "frequency": 1234}),  # Frequency shouldn't matter
            Link.LinkType.ETHERNET,
        )

        self.assertEqual(
            get_link_type({"type": "pon", "frequency": None}),
            Link.LinkType.FIBER,
        )

        self.assertEqual(
            get_link_type({"type": "pon", "frequency": 1234}),  # Frequency shouldn't matter
            Link.LinkType.FIBER,
        )

        with pytest.raises(ValueError):
            get_link_type({"type": "other", "frequency": 1234, "id": "abc"}),

    def test_get_building_from_network_number(self):
        node1 = Node(
            network_number=1234,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node1.save()

        node2 = Node(
            network_number=5678,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node2.save()

        node3 = Node(
            network_number=9012,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node3.save()

        building1 = Building(latitude=0, longitude=0, address_truth_sources=[])
        building1.primary_node = node1
        building1.save()

        building2 = Building(latitude=0, longitude=0, address_truth_sources=[])
        building2.primary_node = node2
        building2.save()
        building2.nodes.add(node1)
        building2.nodes.add(node3)

        self.assertEqual(get_building_from_network_number(node1.network_number), building1)
        self.assertEqual(get_building_from_network_number(node2.network_number), building2)
        self.assertEqual(get_building_from_network_number(node3.network_number), building2)

    @patch("meshapi.util.uisp_import.utils.get_uisp_device_detail")
    @patch("meshapi.util.uisp_import.utils.get_uisp_session")
    def test_get_uisp_link_last_seen(self, mock_get_session, mock_get_device):
        mock_get_device.side_effect = [
            {"overview": {"lastSeen": "2018-11-14T15:20:32.004Z"}},
            {"overview": {"lastSeen": "2020-11-14T15:20:32.004Z"}},
            {"overview": {"lastSeen": "2016-11-14T15:20:32.004Z"}},
            {"overview": {"lastSeen": "2020-11-14T15:20:32.004Z"}},
        ]

        last_seen = get_uisp_link_last_seen(
            "mock_from_uuid",
            "mock_to_uuid",
            "mock_session",
        )

        mock_get_device.assert_has_calls(
            [
                call("mock_from_uuid", "mock_session"),
                call("mock_to_uuid", "mock_session"),
            ]
        )

        self.assertEqual(
            last_seen,
            datetime.datetime(2018, 11, 14, 15, 20, 32, 4000, tzinfo=tzutc()),
        )

        mock_get_session.assert_not_called()

        last_seen = get_uisp_link_last_seen(
            "mock_from_uuid",
            "mock_to_uuid",
        )
        mock_get_session.assert_called_once()

        self.assertEqual(
            last_seen,
            datetime.datetime(2016, 11, 14, 15, 20, 32, 4000, tzinfo=tzutc()),
        )

    @patch("meshapi.util.uisp_import.utils.notify_administrators_of_data_issue")
    def test_notify_admins_of_changes(self, mock_notify):
        node1 = Node(
            network_number=1234,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node1.save()

        device = Device(node=node1, status=Device.DeviceStatus.ACTIVE)
        device.save()

        notify_admins_of_changes(device, ["Mock change 1", "Mock change 2"])

        mock_notify.assert_called_once_with(
            [device],
            DeviceSerializer,
            message="modified device based on information from UISP. The following changes were made:\n"
            " - Mock change 1\n"
            " - Mock change 2\n"
            "(to prevent this, make changes to these fields in UISP rather than directly in MeshDB)",
        )


class TestUISPImportUpdateObjects(TestCase):
    def setUp(self):
        self.node1 = Node(
            network_number=1234,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        self.node1.save()

        self.node2 = Node(
            network_number=5678,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        self.node2.save()

        self.node3 = Node(
            network_number=9012,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        self.node3.save()

        self.device1 = Device(
            node=self.node1,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-1234-dev1",
        )
        self.device1.save()

        self.device2 = Device(
            node=self.node2,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-5678-dev2",
        )
        self.device2.save()

        self.device3 = Device(
            node=self.node3,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-9012-dev3",
        )
        self.device3.save()

        self.link = Link(
            from_device=self.device1,
            to_device=self.device2,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIVE_GHZ,
        )
        self.link.save()

    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_update_link_many_changes(self, mock_get_last_seen):
        last_seen_date = datetime.datetime(2018, 11, 14, 15, 20, 32, 4000, tzinfo=tzutc())
        mock_get_last_seen.return_value = last_seen_date

        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_from_device=self.device1,
            uisp_to_device=self.device3,
            uisp_status=Link.LinkStatus.INACTIVE,
            uisp_link_type=Link.LinkType.SIXTY_GHZ,
        )

        self.link.refresh_from_db()
        self.assertEqual(self.link.from_device, self.device1)
        self.assertEqual(self.link.to_device, self.device3)
        self.assertEqual(self.link.status, Link.LinkStatus.INACTIVE)
        self.assertEqual(self.link.type, Link.LinkType.SIXTY_GHZ)
        self.assertEqual(self.link.abandon_date, last_seen_date.date())

        self.assertEqual(
            change_messages,
            [
                "Changed connected device pair from [nycmesh-1234-dev1, nycmesh-5678-dev2] to [nycmesh-1234-dev1, nycmesh-9012-dev3]",
                "Marked as Inactive due to being offline for more than 30 days",
                "Changed link type from 5 GHz to 60 GHz",
            ],
        )

    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_update_link_add_abandon_date(self, mock_get_last_seen):
        self.link.status = Link.LinkStatus.INACTIVE
        self.link.save()

        last_seen_date = datetime.datetime(2018, 11, 14, 15, 20, 32, 4000, tzinfo=tzutc())
        mock_get_last_seen.return_value = last_seen_date

        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_from_device=self.device1,
            uisp_to_device=self.device2,
            uisp_status=Link.LinkStatus.INACTIVE,
            uisp_link_type=Link.LinkType.FIVE_GHZ,
        )

        self.link.refresh_from_db()
        self.assertEqual(self.link.from_device, self.device1)
        self.assertEqual(self.link.to_device, self.device2)
        self.assertEqual(self.link.status, Link.LinkStatus.INACTIVE)
        self.assertEqual(self.link.type, Link.LinkType.FIVE_GHZ)
        self.assertEqual(self.link.abandon_date, last_seen_date.date())

        self.assertEqual(
            change_messages,
            [
                "Added missing abandon date of 2018-11-14 based on UISP last-seen",
            ],
        )

    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_update_link_not_offline_long_enough(self, mock_get_last_seen):
        last_seen_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)
        mock_get_last_seen.return_value = last_seen_date

        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_from_device=self.device1,
            uisp_to_device=self.device2,
            uisp_status=Link.LinkStatus.INACTIVE,
            uisp_link_type=Link.LinkType.FIVE_GHZ,
        )

        self.link.refresh_from_db()
        self.assertEqual(self.link.from_device, self.device1)
        self.assertEqual(self.link.to_device, self.device2)
        self.assertEqual(self.link.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(self.link.type, Link.LinkType.FIVE_GHZ)
        self.assertEqual(self.link.abandon_date, None)

        self.assertEqual(change_messages, [])

    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_update_link_reactivate_old_device(self, mock_get_last_seen):
        self.link.status = Link.LinkStatus.INACTIVE
        self.link.abandon_date = datetime.date(2018, 11, 14)
        self.link.save()

        last_seen_date = datetime.datetime.now(datetime.timezone.utc)
        mock_get_last_seen.return_value = last_seen_date

        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_from_device=self.device1,
            uisp_to_device=self.device2,
            uisp_status=Link.LinkStatus.ACTIVE,
            uisp_link_type=Link.LinkType.FIVE_GHZ,
        )

        self.link.refresh_from_db()
        self.assertEqual(self.link.from_device, self.device1)
        self.assertEqual(self.link.to_device, self.device2)
        self.assertEqual(self.link.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(self.link.type, Link.LinkType.FIVE_GHZ)
        self.assertEqual(self.link.abandon_date, None)

        self.assertEqual(
            change_messages,
            [
                "Marked as Active due to coming back online in UISP. Warning: this link was "
                "previously abandoned on 2018-11-14, if this link has been re-purposed, "
                "please make sure the device names and network numbers are updated to reflect the new location"
            ],
        )

    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_update_link_no_changes(self, mock_get_last_seen):
        mock_get_last_seen.return_value = datetime.datetime.now(datetime.timezone.utc)

        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_from_device=self.device1,
            uisp_to_device=self.device2,
            uisp_status=Link.LinkStatus.ACTIVE,
            uisp_link_type=Link.LinkType.FIVE_GHZ,
        )
        self.assertEqual(change_messages, [])

        # Swapping from/to should have no impact
        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_from_device=self.device2,
            uisp_to_device=self.device1,
            uisp_status=Link.LinkStatus.ACTIVE,
            uisp_link_type=Link.LinkType.FIVE_GHZ,
        )
        self.assertEqual(change_messages, [])

        self.link.refresh_from_db()
        self.assertEqual(self.link.from_device, self.device1)
        self.assertEqual(self.link.to_device, self.device2)
        self.assertEqual(self.link.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(self.link.type, Link.LinkType.FIVE_GHZ)
        self.assertEqual(self.link.abandon_date, None)

    def test_update_device_many_changes(self):
        last_seen_date = datetime.datetime(2018, 11, 14, 15, 20, 32, 4000, tzinfo=tzutc())
        change_messages = update_device_from_uisp_data(
            self.device1,
            uisp_node=self.node2,
            uisp_name="nycmesh-5678-dev1",
            uisp_status=Device.DeviceStatus.INACTIVE,
            uisp_last_seen=last_seen_date,
        )

        self.device1.refresh_from_db()
        self.assertEqual(self.device1.name, "nycmesh-5678-dev1")
        self.assertEqual(self.device1.node, self.node2)
        self.assertEqual(self.device1.status, Device.DeviceStatus.INACTIVE)
        self.assertEqual(self.device1.abandon_date, last_seen_date.date())

        self.assertEqual(
            change_messages,
            [
                'Changed name from "nycmesh-1234-dev1" to "nycmesh-5678-dev1"',
                "Changed network number from 1234 to 5678",
                "Marked as Inactive due to being offline for more than 30 days",
            ],
        )

    def test_update_device_add_abandon_date(self):
        self.device1.status = Device.DeviceStatus.INACTIVE
        self.device1.save()

        last_seen_date = datetime.datetime(2018, 11, 14, 15, 20, 32, 4000, tzinfo=tzutc())
        change_messages = update_device_from_uisp_data(
            self.device1,
            uisp_node=self.node1,
            uisp_name="nycmesh-1234-dev1",
            uisp_status=Device.DeviceStatus.INACTIVE,
            uisp_last_seen=last_seen_date,
        )

        self.device1.refresh_from_db()
        self.assertEqual(self.device1.name, "nycmesh-1234-dev1")
        self.assertEqual(self.device1.node, self.node1)
        self.assertEqual(self.device1.status, Device.DeviceStatus.INACTIVE)
        self.assertEqual(self.device1.abandon_date, last_seen_date.date())

        self.assertEqual(
            change_messages,
            [
                "Added missing abandon date of 2018-11-14 based on UISP last-seen",
            ],
        )

    def test_update_device_reactivate_old_device(self):
        self.device1.status = Device.DeviceStatus.INACTIVE
        self.device1.abandon_date = datetime.date(2018, 11, 14)
        self.device1.save()

        last_seen_date = datetime.datetime.now(datetime.timezone.utc)
        change_messages = update_device_from_uisp_data(
            self.device1,
            uisp_node=self.node1,
            uisp_name="nycmesh-1234-dev1",
            uisp_status=Device.DeviceStatus.ACTIVE,
            uisp_last_seen=last_seen_date,
        )

        self.device1.refresh_from_db()
        self.assertEqual(self.device1.name, "nycmesh-1234-dev1")
        self.assertEqual(self.device1.node, self.node1)
        self.assertEqual(self.device1.status, Device.DeviceStatus.ACTIVE)
        self.assertEqual(self.device1.abandon_date, None)

        self.assertEqual(
            change_messages,
            [
                "Marked as Active due to coming back online in UISP. Warning: this device was "
                "previously abandoned on 2018-11-14, if this device has been re-purposed, "
                "please make sure the device name and network number are updated to reflect the new location "
                "and function"
            ],
        )

    def test_update_device_no_changes(self):
        last_seen_date = datetime.datetime.now(datetime.timezone.utc)
        change_messages = update_device_from_uisp_data(
            self.device1,
            uisp_node=self.node1,
            uisp_name="nycmesh-1234-dev1",
            uisp_status=Device.DeviceStatus.ACTIVE,
            uisp_last_seen=last_seen_date,
        )

        self.device1.refresh_from_db()
        self.assertEqual(self.device1.name, "nycmesh-1234-dev1")
        self.assertEqual(self.device1.node, self.node1)
        self.assertEqual(self.device1.status, Device.DeviceStatus.ACTIVE)
        self.assertEqual(self.device1.abandon_date, None)

        self.assertEqual(change_messages, [])


class TestUISPImportHandlers(TestCase):
    def setUp(self):
        self.node1 = Node(
            network_number=1234,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        self.node1.save()

        self.node2 = Node(
            network_number=5678,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        self.node2.save()

        self.node3 = Node(
            network_number=9012,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        self.node3.save()

        self.node4 = Node(
            network_number=3456,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        self.node4.save()

        self.building1 = Building(latitude=0, longitude=0, address_truth_sources=[])
        self.building1.primary_node = self.node1
        self.building1.save()

        self.building2 = Building(latitude=0, longitude=0, address_truth_sources=[])
        self.building2.primary_node = self.node2
        self.building2.save()

        self.building3 = Building(latitude=0, longitude=0, address_truth_sources=[])
        self.building3.primary_node = self.node3
        self.building3.save()

        self.building4 = Building(latitude=0, longitude=0, address_truth_sources=[])
        self.building4.primary_node = self.node4
        self.building4.save()

        self.device1 = Device(
            node=self.node1,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-1234-dev1",
            uisp_id="uisp-uuid1",
        )
        self.device1.save()

        self.device2 = Device(
            node=self.node2,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-5678-dev2",
            uisp_id="uisp-uuid2",
        )
        self.device2.save()

        self.device3 = Device(
            node=self.node3,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-9012-dev3",
            uisp_id="uisp-uuid3",
        )
        self.device3.save()

        self.device4 = Device(
            node=self.node3,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-7890-dev4",
            uisp_id="uisp-uuid4",
        )
        self.device4.save()

        self.link1 = Link(
            from_device=self.device1,
            to_device=self.device2,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIVE_GHZ,
            uisp_id="uisp-uuid1",
        )
        self.link1.save()

        self.link2 = Link(
            from_device=self.device1,
            to_device=self.device3,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIVE_GHZ,
            uisp_id="uisp-uuid2",
        )
        self.link2.save()

    @patch("meshapi.util.uisp_import.handler.notify_admins_of_changes")
    @patch("meshapi.util.uisp_import.handler.update_device_from_uisp_data")
    def test_import_and_sync_devices(self, mock_update_device, mock_notify_admins):
        mock_update_device.side_effect = [
            [],
            [],
            ["Mock update 3"],
        ]

        uisp_devices = [
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                },
                "identification": {
                    "id": "uisp-uuid1",
                    "name": "nycmesh-1234-dev1",
                    "category": "wireless",
                },
            },
            {
                "overview": {
                    "status": None,
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                },
                "identification": {
                    "id": "uisp-uuid2",
                    "name": "nycmesh-5678-dev2",
                    "category": "wireless",
                },
            },
            {
                "overview": {
                    "status": "inactive",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                },
                "identification": {
                    "id": "uisp-uuid3",
                    "name": "nycmesh-9012-dev3",
                    "category": "wireless",
                },
            },
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                },
                "identification": {
                    "id": "uisp-uuid9",
                    "name": "nycmesh-1234-dev9",
                    "category": "wireless",
                },
            },
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                },
                "identification": {
                    "id": "uisp-uuid5",
                    "name": "nycmesh-7777-abc",
                    "category": "optical",  # Causes it to be excluded
                },
            },
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                },
                "identification": {
                    "id": "uisp-uuid5",
                    "name": "nycmesh-abc-def",  # Causes it to be excluded, no NN
                    "category": "wireless",
                },
            },
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                },
                "identification": {
                    "id": "uisp-uuid5",
                    "name": "nycmesh-888-def",  # Causes it to be excluded, no NN 888 in the DB
                    "category": "wireless",
                },
            },
        ]

        import_and_sync_uisp_devices(uisp_devices)

        last_seen_date = datetime.datetime(2024, 8, 12, 2, 4, 35, 335000, tzinfo=tzutc())
        mock_update_device.assert_has_calls(
            [
                call(self.device1, self.node1, "nycmesh-1234-dev1", Device.DeviceStatus.ACTIVE, last_seen_date),
                call(self.device2, self.node2, "nycmesh-5678-dev2", Device.DeviceStatus.ACTIVE, last_seen_date),
                call(self.device3, self.node3, "nycmesh-9012-dev3", Device.DeviceStatus.INACTIVE, last_seen_date),
            ]
        )

        mock_notify_admins.assert_called_once_with(self.device3, ["Mock update 3"])

        created_device = Device.objects.get(uisp_id="uisp-uuid9")
        self.assertEqual(created_device.node, self.node1)
        self.assertEqual(created_device.name, "nycmesh-1234-dev9")
        self.assertEqual(created_device.status, Device.DeviceStatus.ACTIVE)
        self.assertEqual(created_device.install_date, datetime.date(2018, 11, 14))
        self.assertEqual(created_device.abandon_date, None)
        self.assertTrue(created_device.notes.startswith("Automatically imported from UISP on"))

        self.assertIsNone(Device.objects.filter(uisp_id="uisp-uuid5").first())

    @patch("meshapi.util.uisp_import.handler.get_uisp_session")
    @patch("meshapi.util.uisp_import.handler.notify_admins_of_changes")
    @patch("meshapi.util.uisp_import.handler.update_link_from_uisp_data")
    def test_import_and_sync_links(self, mock_update_link, mock_notify_admins, mock_get_uisp_session):
        mock_update_link.side_effect = [
            [],
            ["Mock update 2"],
        ]
        mock_get_uisp_session.return_value = "mock_uisp_session"

        uisp_links = [
            {
                "from": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid1",
                            "category": "wireless",
                            "name": "nycmesh-1234-dev1",
                        }
                    }
                },
                "to": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid2",
                            "category": "wireless",
                            "name": "nycmesh-5678-dev2",
                        }
                    }
                },
                "state": "active",
                "id": "uisp-uuid1",
                "type": "wireless",
                "frequency": 5_000,
            },
            {
                "from": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid1",
                            "category": "wireless",
                            "name": "nycmesh-1234-dev1",
                        }
                    }
                },
                "to": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid3",
                            "category": "wireless",
                            "name": "nycmesh-9012-dev3",
                        }
                    }
                },
                "state": "inactive",
                "id": "uisp-uuid2",
                "type": "wireless",
                "frequency": 60_000,
            },
            {
                "from": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid2",
                            "category": "wireless",
                            "name": "nycmesh-5678-dev2",
                        }
                    }
                },
                "to": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid4",
                            "category": "wireless",
                            "name": "nycmesh-7890-dev4",
                        }
                    }
                },
                "state": "active",
                "id": "uisp-uuid3",
                "type": "wireless",
                "frequency": 5_000,
            },
            {
                "from": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid2",
                            "category": "wireless",
                            "name": "nycmesh-5678-dev2",
                        }
                    }
                },
                "to": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid-non-existent",  # Causes this link to be excluded
                            "category": "wireless",
                            "name": "nycmesh-3456-dev4",
                        }
                    }
                },
                "state": "active",
                "id": "uisp-uuid4",
                "type": "wireless",
                "frequency": 5_000,
            },
            {
                "from": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid-non-existent",  # Causes this link to be excluded
                            "category": "wireless",
                            "name": "nycmesh-5678-dev2",
                        }
                    }
                },
                "to": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid3",
                            "category": "wireless",
                            "name": "nycmesh-9012-dev3",
                        }
                    }
                },
                "state": "active",
                "id": "uisp-uuid4",
                "type": "wireless",
                "frequency": 5_000,
            },
        ]

        import_and_sync_uisp_links(uisp_links)

        mock_update_link.assert_has_calls(
            [
                call(
                    self.link1,
                    self.device1,
                    self.device2,
                    Link.LinkStatus.ACTIVE,
                    Link.LinkType.FIVE_GHZ,
                    "mock_uisp_session",
                ),
                call(
                    self.link2,
                    self.device1,
                    self.device3,
                    Link.LinkStatus.INACTIVE,
                    Link.LinkType.SIXTY_GHZ,
                    "mock_uisp_session",
                ),
            ]
        )

        mock_notify_admins.assert_called_once_with(self.link2, ["Mock update 2"])

        created_link = Link.objects.get(uisp_id="uisp-uuid3")
        self.assertEqual(created_link.from_device, self.device2)
        self.assertEqual(created_link.to_device, self.device4)
        self.assertEqual(created_link.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(created_link.type, Link.LinkType.FIVE_GHZ)
        self.assertEqual(created_link.install_date, None)
        self.assertEqual(created_link.abandon_date, None)
        self.assertEqual(created_link.description, None)
        self.assertTrue(created_link.notes.startswith("Automatically imported from UISP on"))

        self.assertIsNone(Link.objects.filter(uisp_id="uisp-uuid4").first())

    def test_sync_links_with_los_update_existing(self):
        los1 = LOS(
            from_building=self.building2,
            to_building=self.building1,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=datetime.date(2020, 1, 1),
        )
        los1.save()

        los2 = LOS(
            from_building=self.building1,
            to_building=self.building3,
            source=LOS.LOSSource.EXISTING_LINK,
            analysis_date=datetime.date(2020, 1, 1),
        )
        los2.save()

        sync_link_table_into_los_objects()

        los1.refresh_from_db()
        self.assertEqual(los1.from_building, self.building2)
        self.assertEqual(los1.to_building, self.building1)
        self.assertEqual(los1.source, LOS.LOSSource.EXISTING_LINK)
        self.assertEqual(los1.analysis_date, datetime.date.today())

        los2.refresh_from_db()
        self.assertEqual(los2.from_building, self.building1)
        self.assertEqual(los2.to_building, self.building3)
        self.assertEqual(los2.source, LOS.LOSSource.EXISTING_LINK)
        self.assertEqual(los2.analysis_date, datetime.date.today())

    def test_sync_links_with_los_inactive_link(self):
        self.link1.status = Link.LinkStatus.INACTIVE
        self.link1.abandon_date = datetime.date(2024, 1, 2)
        self.link1.save()

        los = LOS(
            from_building=self.building2,
            to_building=self.building1,
            source=LOS.LOSSource.EXISTING_LINK,
            analysis_date=datetime.date(2020, 1, 1),
        )
        los.save()

        sync_link_table_into_los_objects()

        los.refresh_from_db()
        self.assertEqual(los.from_building, self.building2)
        self.assertEqual(los.to_building, self.building1)
        self.assertEqual(los.source, LOS.LOSSource.EXISTING_LINK)
        self.assertEqual(los.analysis_date, datetime.date(2024, 1, 2))

    def test_sync_links_with_add_new_los(self):
        los = LOS(
            from_building=self.building2,
            to_building=self.building1,
            source=LOS.LOSSource.EXISTING_LINK,
            analysis_date=datetime.date(2020, 1, 1),
        )
        los.save()

        sync_link_table_into_los_objects()

        los.refresh_from_db()
        self.assertEqual(los.from_building, self.building2)
        self.assertEqual(los.to_building, self.building1)
        self.assertEqual(los.source, LOS.LOSSource.EXISTING_LINK)
        self.assertEqual(los.analysis_date, datetime.date.today())

        new_los = LOS.objects.get(from_building=self.building1, to_building=self.building3)
        self.assertEqual(new_los.source, LOS.LOSSource.EXISTING_LINK)
        self.assertEqual(new_los.analysis_date, datetime.date.today())
        self.assertEqual(new_los.notes, f"Created automatically from Link ID {self.link2.id} (NN1234 → NN9012)\n\n")

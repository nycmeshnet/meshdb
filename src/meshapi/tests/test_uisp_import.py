import datetime
import uuid
from unittest.mock import call, patch

import pytest
from dateutil.tz import tzutc
from django.test import TestCase, TransactionTestCase

from meshapi.models import LOS, AccessPoint, Building, Device, Link, Node, Sector
from meshapi.serializers import AccessPointSerializer, DeviceSerializer, LinkSerializer, SectorSerializer
from meshapi.util.uisp_import.sync_handlers import (
    import_and_sync_uisp_devices,
    import_and_sync_uisp_links,
    sync_link_table_into_los_objects,
)
from meshapi.util.uisp_import.update_objects import update_device_from_uisp_data, update_link_from_uisp_data
from meshapi.util.uisp_import.utils import (
    get_building_from_network_number,
    get_link_type,
    get_uisp_link_last_seen,
    guess_compass_heading_from_device_name,
    notify_admins_of_changes,
    parse_uisp_datetime,
)


class TestUISPImportUtils(TestCase):
    def test_guess_compass_heading(self):
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-north"), 0)
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-south"), 180)
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-east"), 90)
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-west"), 270)

        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-northwest"), 315)
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-eastsouth"), 135)

        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-northeasteast"), 67.5)
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-eastsoutheast"), 112.5)
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-southsoutheast"), 157.5)
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-westsouthwest"), 247.5)
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-northnorthwest"), 337.5)

        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-ev"), None)
        self.assertEqual(guess_compass_heading_from_device_name("nycmesh-227-sector1"), None)

        with pytest.raises(ValueError):
            guess_compass_heading_from_device_name("nycmesh-227-northsouth")

        with pytest.raises(ValueError):
            guess_compass_heading_from_device_name("nycmesh-227-northsoutheast")

        with pytest.raises(ValueError):
            guess_compass_heading_from_device_name("nycmesh-227-westeast")

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
            #  https://github.com/nycmeshnet/meshdb/issues/518
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
            {"overview": {"lastSeen": None}},
            {"overview": {"lastSeen": "2020-11-14T15:20:32.004Z"}},
            {"overview": {"lastSeen": None}},
            {"overview": {"lastSeen": None}},
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

        last_seen = get_uisp_link_last_seen(
            "mock_from_uuid",
            "mock_to_uuid",
        )
        self.assertEqual(
            last_seen,
            datetime.datetime(2020, 11, 14, 15, 20, 32, 4000, tzinfo=tzutc()),
        )
        last_seen = get_uisp_link_last_seen(
            "mock_from_uuid",
            "mock_to_uuid",
        )
        self.assertEqual(
            last_seen,
            None,
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

    @patch("meshapi.util.uisp_import.utils.notify_administrators_of_data_issue")
    def test_notify_admins_of_created_sector(self, mock_notify):
        node1 = Node(
            network_number=1234,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node1.save()

        sector = Sector(
            node=node1,
            status=Device.DeviceStatus.ACTIVE,
            radius=1,
            azimuth=0,
            width=90,
        )
        sector.save()

        notify_admins_of_changes(sector, ["Mock change 1", "Mock change 2"], created=True)

        mock_notify.assert_called_once_with(
            [sector],
            SectorSerializer,
            message="created sector based on information from UISP. The following items may require attention:\n"
            " - Mock change 1\n"
            " - Mock change 2",
        )
        mock_notify.reset_mock()

        # Test automatic sector detection
        notify_admins_of_changes(sector.device_ptr, ["Mock change 1", "Mock change 2"], created=True)

        mock_notify.assert_called_once_with(
            [sector],
            SectorSerializer,
            message="created sector based on information from UISP. The following items may require attention:\n"
            " - Mock change 1\n"
            " - Mock change 2",
        )

    @patch("meshapi.util.uisp_import.utils.notify_administrators_of_data_issue")
    def test_notify_admins_autodetect_ap(self, mock_notify):
        node1 = Node(
            network_number=1234,
            status=Node.NodeStatus.ACTIVE,
            type=Node.NodeType.STANDARD,
            latitude=0,
            longitude=0,
        )
        node1.save()

        ap = AccessPoint(
            node=node1,
            status=Device.DeviceStatus.ACTIVE,
            latitude=0,
            longitude=0,
        )
        ap.save()

        # We pass the device object here, and confirm that the notification function
        # automatically detects that this is device is associated with an AccessPoint and fetches
        # the relevant object (this makes the admin link correct)
        notify_admins_of_changes(ap.device_ptr, ["Mock change 1", "Mock change 2"], created=True)

        mock_notify.assert_called_once_with(
            [ap],
            AccessPointSerializer,
            message="created access point based on information from UISP. The following items may require attention:\n"
            " - Mock change 1\n"
            " - Mock change 2",
        )


class TestUISPImportUpdateObjects(TransactionTestCase):
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
            uisp_id="fake-uisp-uuid",
        )
        self.link.save()

    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_update_link_many_changes(self, mock_get_last_seen):
        last_seen_date = datetime.datetime(2018, 11, 14, 15, 20, 32, 4000, tzinfo=tzutc())
        mock_get_last_seen.return_value = last_seen_date

        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_link_id="fake-uisp-uuid2",
            uisp_from_device=self.device1,
            uisp_to_device=self.device3,
            uisp_status=Link.LinkStatus.INACTIVE,
        )

        self.link.refresh_from_db()
        self.assertEqual(self.link.uisp_id, "fake-uisp-uuid2")
        self.assertEqual(self.link.from_device, self.device1)
        self.assertEqual(self.link.to_device, self.device3)
        self.assertEqual(self.link.status, Link.LinkStatus.INACTIVE)
        self.assertEqual(self.link.type, Link.LinkType.FIVE_GHZ)
        self.assertEqual(self.link.abandon_date, last_seen_date.date())

        self.assertEqual(
            change_messages,
            [
                "Changed UISP link ID to fake-uisp-uuid2",
                "Changed connected device pair from [nycmesh-1234-dev1, nycmesh-5678-dev2] to [nycmesh-1234-dev1, nycmesh-9012-dev3]",
                "Marked as Inactive due to it being offline in UISP for more than 30 days",
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
            uisp_link_id="fake-uisp-uuid",
            uisp_from_device=self.device1,
            uisp_to_device=self.device2,
            uisp_status=Link.LinkStatus.INACTIVE,
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
            uisp_link_id="fake-uisp-uuid",
            uisp_from_device=self.device1,
            uisp_to_device=self.device2,
            uisp_status=Link.LinkStatus.INACTIVE,
        )

        self.link.refresh_from_db()
        self.assertEqual(self.link.from_device, self.device1)
        self.assertEqual(self.link.to_device, self.device2)
        self.assertEqual(self.link.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(self.link.type, Link.LinkType.FIVE_GHZ)
        self.assertEqual(self.link.abandon_date, None)

        self.assertEqual(change_messages, [])

    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_update_link_unknown_offline_duration(self, mock_get_last_seen):
        mock_get_last_seen.return_value = None

        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_link_id="fake-uisp-uuid",
            uisp_from_device=self.device1,
            uisp_to_device=self.device2,
            uisp_status=Link.LinkStatus.INACTIVE,
        )

        self.link.refresh_from_db()
        self.assertEqual(self.link.from_device, self.device1)
        self.assertEqual(self.link.to_device, self.device2)
        self.assertEqual(self.link.status, Link.LinkStatus.INACTIVE)
        self.assertEqual(self.link.type, Link.LinkType.FIVE_GHZ)
        self.assertEqual(self.link.abandon_date, None)

        self.assertEqual(change_messages, ["Marked as Inactive due to it being offline in UISP"])

    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_update_link_reactivate_old_device(self, mock_get_last_seen):
        self.link.status = Link.LinkStatus.INACTIVE
        self.link.abandon_date = datetime.date(2018, 11, 14)
        self.link.save()

        last_seen_date = datetime.datetime.now(datetime.timezone.utc)
        mock_get_last_seen.return_value = last_seen_date

        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_link_id="fake-uisp-uuid",
            uisp_from_device=self.device1,
            uisp_to_device=self.device2,
            uisp_status=Link.LinkStatus.ACTIVE,
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
                "Marked as Active due to it coming back online in UISP. Warning: this link was "
                "previously abandoned on 2018-11-14, if this link has been re-purposed, "
                "please make sure the device names and network numbers are updated to reflect the new location"
            ],
        )

    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_update_link_no_changes(self, mock_get_last_seen):
        mock_get_last_seen.return_value = datetime.datetime.now(datetime.timezone.utc)

        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_link_id="fake-uisp-uuid",
            uisp_from_device=self.device1,
            uisp_to_device=self.device2,
            uisp_status=Link.LinkStatus.ACTIVE,
        )
        self.assertEqual(change_messages, [])

        # Swapping from/to should have no impact
        change_messages = update_link_from_uisp_data(
            self.link,
            uisp_link_id="fake-uisp-uuid",
            uisp_from_device=self.device2,
            uisp_to_device=self.device1,
            uisp_status=Link.LinkStatus.ACTIVE,
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
                "Marked as Inactive due to it being offline in UISP for more than 30 days",
            ],
        )

    def test_update_device_uncertain_offline_duration(self):
        change_messages = update_device_from_uisp_data(
            self.device1,
            uisp_node=self.node1,
            uisp_name="nycmesh-1234-dev1",
            uisp_status=Device.DeviceStatus.INACTIVE,
            uisp_last_seen=None,
        )

        self.device1.refresh_from_db()
        self.assertEqual(self.device1.name, "nycmesh-1234-dev1")
        self.assertEqual(self.device1.node, self.node1)
        self.assertEqual(self.device1.status, Device.DeviceStatus.INACTIVE)
        self.assertEqual(self.device1.abandon_date, None)

        self.assertEqual(
            change_messages,
            [
                "Marked as Inactive due to it being offline in UISP",
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
                "Marked as Active due to it coming back online in UISP. Warning: this device was "
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


class TestUISPImportHandlers(TransactionTestCase):
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

        self.device5 = Device(
            node=self.node3,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-7890-dev5",
            uisp_id="uisp-uuid-not-real-dont-match-me",
        )
        self.device5.save()

        self.device6 = Device(
            node=self.node3,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-7890-dev6",
            uisp_id="uisp-uuid6",
        )
        self.device6.save()

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

        self.link3 = Link(
            from_device=self.device2,
            to_device=self.device3,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIVE_GHZ,
            uisp_id="uisp-uuid-not-real-dont-match-me",
        )
        self.link3.save()

        self.link4 = Link(
            from_device=self.device1,
            to_device=self.device6,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.ETHERNET,
            uisp_id="uisp-uuid40a",
        )
        self.link4.save()

        self.link5a = Link(
            from_device=self.device2,
            to_device=self.device6,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.ETHERNET,
            uisp_id="uisp-uuid50a",
        )
        self.link5a.save()

        self.link5b = Link(
            from_device=self.device2,
            to_device=self.device6,
            status=Link.LinkStatus.INACTIVE,
            type=Link.LinkType.ETHERNET,
            uisp_id="uisp-uuid50b",
        )
        self.link5b.save()

        self.link6a = Link(
            from_device=self.device3,
            to_device=self.device6,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIBER,
            uisp_id="uisp-uuid60a",
        )
        self.link6a.save()

        self.link6b = Link(
            from_device=self.device3,
            to_device=self.device6,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIBER,
            uisp_id="uisp-uuid60b",
        )
        self.link6b.save()

    @patch("meshapi.util.uisp_import.sync_handlers.notify_admins_of_changes")
    @patch("meshapi.util.uisp_import.sync_handlers.update_device_from_uisp_data")
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
                    "wirelessMode": "sta-ptmp",
                },
                "identification": {
                    "id": "uisp-uuid1",
                    "name": "nycmesh-1234-dev1",
                    "category": "wireless",
                    "type": "airMax",
                },
            },
            {
                "overview": {
                    "status": None,
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                    "wirelessMode": "sta-ptmp",
                },
                "identification": {
                    "id": "uisp-uuid2",
                    "name": "nycmesh-5678-dev2",
                    "category": "wireless",
                    "type": "airMax",
                },
            },
            {
                "overview": {
                    "status": "inactive",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                    "wirelessMode": "sta-ptmp",
                },
                "identification": {
                    "id": "uisp-uuid3",
                    "name": "nycmesh-9012-dev3",
                    "category": "wireless",
                    "type": "airMax",
                },
            },
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                    "wirelessMode": "sta-ptmp",
                },
                "identification": {
                    "id": "uisp-uuid9",
                    "name": "nycmesh-1234-dev9",
                    "category": "wireless",
                    "type": "airMax",
                },
            },
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                    "wirelessMode": "ap-ptmp",
                },
                "identification": {
                    "id": "uisp-uuid99",
                    "name": "nycmesh-1234-east",
                    "model": "LAP-120",
                    "category": "wireless",
                    "type": "airMax",
                },
            },
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                    "wirelessMode": "sta-ptmp",
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
                    "wirelessMode": "sta-ptmp",
                },
                "identification": {
                    "id": "uisp-uuid5",
                    "name": "nycmesh-abc-def",  # Causes it to be excluded, no NN
                    "category": "wireless",
                    "type": "airMax",
                },
            },
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                    "wirelessMode": "sta-ptmp",
                },
                "identification": {
                    "id": "uisp-uuid5",
                    "name": "nycmesh-888-def",  # Causes it to be excluded, no NN 888 in the DB
                    "category": "wireless",
                    "type": "airMax",
                },
            },
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                    "wirelessMode": "ap-ptmp",
                },
                "identification": {
                    "id": "uisp-uuid999",
                    "name": "nycmesh-1234-northsouth",  # this direction makes no sense, causes guess of 0 deg
                    "model": "LAP-120",
                    "category": "wireless",
                    "type": "airMax",
                },
            },
        ]

        import_and_sync_uisp_devices(uisp_devices)

        self.device5.refresh_from_db()
        self.assertEqual(self.device5.status, Device.DeviceStatus.INACTIVE)

        created_sector1 = Sector.objects.get(uisp_id="uisp-uuid99")
        created_sector2 = Sector.objects.get(uisp_id="uisp-uuid999")

        last_seen_date = datetime.datetime(2024, 8, 12, 2, 4, 35, 335000, tzinfo=tzutc())
        mock_update_device.assert_has_calls(
            [
                call(self.device1, self.node1, "nycmesh-1234-dev1", Device.DeviceStatus.ACTIVE, last_seen_date),
                call(self.device2, self.node2, "nycmesh-5678-dev2", Device.DeviceStatus.ACTIVE, last_seen_date),
                call(self.device3, self.node3, "nycmesh-9012-dev3", Device.DeviceStatus.INACTIVE, last_seen_date),
            ]
        )

        mock_notify_admins.assert_has_calls(
            [
                call(self.device3, ["Mock update 3"]),
                call(
                    created_sector1,
                    [
                        "Guessed azimuth of 90.0 degrees from device name. Please provide a more accurate value if available",
                        "Guessed coverage width of 120 degrees from device type. Please provide a more accurate value if available",
                        "Set default radius of 1 km. Please correct if this is not accurate",
                    ],
                    created=True,
                ),
                call(
                    created_sector2,
                    [
                        "Azimuth defaulted to 0 degrees. Device name did not indicate a cardinal direction. Please provide a more accurate value if available",
                        "Guessed coverage width of 120 degrees from device type. Please provide a more accurate value if available",
                        "Set default radius of 1 km. Please correct if this is not accurate",
                    ],
                    created=True,
                ),
                call(
                    self.device4,
                    [
                        "Marked as inactive because there is no corresponding device in UISP, "
                        "it was probably deleted there",
                    ],
                ),
                call(
                    self.device6,
                    [
                        "Marked as inactive because there is no corresponding device in UISP, "
                        "it was probably deleted there",
                    ],
                ),
                call(
                    self.device5,
                    [
                        "Marked as inactive because there is no corresponding device in UISP, "
                        "it was probably deleted there",
                    ],
                ),
            ]
        )

        created_device = Device.objects.get(uisp_id="uisp-uuid9")
        self.assertEqual(created_device.node, self.node1)
        self.assertEqual(created_device.name, "nycmesh-1234-dev9")
        self.assertEqual(created_device.status, Device.DeviceStatus.ACTIVE)
        self.assertEqual(created_device.install_date, datetime.date(2018, 11, 14))
        self.assertEqual(created_device.abandon_date, None)
        self.assertTrue(created_device.notes.startswith("Automatically imported from UISP on"))

        self.assertEqual(created_sector1.node, self.node1)
        self.assertEqual(created_sector1.name, "nycmesh-1234-east")
        self.assertEqual(created_sector1.status, Device.DeviceStatus.ACTIVE)
        self.assertEqual(created_sector1.install_date, datetime.date(2018, 11, 14))
        self.assertEqual(created_sector1.abandon_date, None)
        self.assertEqual(created_sector1.width, 120)  # From device model
        self.assertEqual(created_sector1.azimuth, 90)  # From device name ("east")
        self.assertEqual(created_sector1.radius, 1)  # Default for airmax sectors
        self.assertTrue(created_sector1.notes.startswith("Automatically imported from UISP on"))

        self.assertEqual(created_sector2.node, self.node1)
        self.assertEqual(created_sector2.name, "nycmesh-1234-northsouth")
        self.assertEqual(created_sector2.status, Device.DeviceStatus.ACTIVE)
        self.assertEqual(created_sector2.install_date, datetime.date(2018, 11, 14))
        self.assertEqual(created_sector2.abandon_date, None)
        self.assertEqual(created_sector2.width, 120)  # From device model
        self.assertEqual(created_sector2.azimuth, 0)  # Default for nonsense device name
        self.assertEqual(created_sector2.radius, 1)  # Default for airmax sectors
        self.assertTrue(created_sector2.notes.startswith("Automatically imported from UISP on"))

        self.assertIsNone(Device.objects.filter(uisp_id="uisp-uuid5").first())

    @patch("meshapi.util.uisp_import.sync_handlers.notify_admins_of_changes")
    @patch("meshapi.util.uisp_import.sync_handlers.update_device_from_uisp_data")
    @patch("meshapi.util.uisp_import.sync_handlers.notify_administrators_of_data_issue")
    def test_duplicate_uisp_id_devices(
        self,
        mock_notify_administrators_of_data_issue,
        mock_update_device,
        mock_notify_admins,
    ):
        uisp_devices = [
            {
                "overview": {
                    "status": "active",
                    "createdAt": "2018-11-14T15:20:32.004Z",
                    "lastSeen": "2024-08-12T02:04:35.335Z",
                    "wirelessMode": "sta-ptmp",
                },
                "identification": {
                    "id": "uisp-uuid12345",
                    "name": "nycmesh-1234-dev1",
                    "category": "wireless",
                    "type": "airMax",
                },
            },
        ]

        dup_device1 = Device(
            node=self.node1,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-1234-dev1",
            uisp_id="uisp-uuid12345",
        )
        dup_device1.save()

        dup_device2 = Sector(
            node=self.node1,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-1234-dev1",
            uisp_id="uisp-uuid12345",
            width=120,
            azimuth=0,
            radius=1,
        )
        dup_device2.save()

        import_and_sync_uisp_devices(uisp_devices)

        mock_update_device.assert_has_calls([])
        mock_notify_admins.assert_has_calls([])

        mock_notify_administrators_of_data_issue.assert_called_once_with(
            [dup_device1, dup_device2],
            DeviceSerializer,
            message="Possible duplicate objects detected, devices share the same UISP ID (uisp-uuid12345)",
        )

        self.assertEqual(2, Device.objects.filter(uisp_id="uisp-uuid12345").count())

    @patch("meshapi.util.uisp_import.sync_handlers.get_uisp_session")
    @patch("meshapi.util.uisp_import.sync_handlers.notify_admins_of_changes")
    @patch("meshapi.util.uisp_import.sync_handlers.update_link_from_uisp_data")
    def test_import_and_sync_links(self, mock_update_link, mock_notify_admins, mock_get_uisp_session):
        mock_update_link.side_effect = [
            [],  # self.link1
            ["Mock update 2"],  # self.link2
        ]
        mock_get_uisp_session.return_value = "mock_uisp_session"

        self.link4.delete()
        self.link5a.delete()
        self.link5b.delete()
        self.link6a.delete()
        self.link6b.delete()

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
                            "id": "uisp-uuid4",
                            "category": "wireless",
                            "name": "nycmesh-3456-dev4",
                        }
                    }
                },
                "state": "active",
                "id": "uisp-uuid5",
                "type": "ethernet",
            },
        ]

        import_and_sync_uisp_links(uisp_links)

        mock_update_link.assert_has_calls(
            [
                call(
                    self.link1,
                    "uisp-uuid1",
                    self.device1,
                    self.device2,
                    Link.LinkStatus.ACTIVE,
                    "mock_uisp_session",
                ),
                call(
                    self.link2,
                    "uisp-uuid2",
                    self.device1,
                    self.device3,
                    Link.LinkStatus.INACTIVE,
                    "mock_uisp_session",
                ),
            ]
        )

        self.link3.refresh_from_db()
        self.assertEqual(self.link3.status, Link.LinkStatus.INACTIVE)

        created_link3 = Link.objects.get(uisp_id="uisp-uuid3")
        created_link5 = Link.objects.get(uisp_id="uisp-uuid5")

        mock_notify_admins.assert_has_calls(
            [
                call(self.link2, ["Mock update 2"]),
                call(
                    created_link5,
                    [
                        "Used link type of 'Ethernet' from UISP metadata, however this may not be correct in the "
                        "case of VPN or Fiber links. Please provide a more accurate value if available"
                    ],
                    created=True,
                ),
                call(
                    self.link3,
                    [
                        "Marked as inactive because there is no corresponding link in UISP, "
                        "it was probably deleted there",
                    ],
                ),
            ]
        )

        self.assertEqual(created_link3.from_device, self.device2)
        self.assertEqual(created_link3.to_device, self.device4)
        self.assertEqual(created_link3.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(created_link3.type, Link.LinkType.FIVE_GHZ)
        self.assertEqual(created_link3.install_date, None)
        self.assertEqual(created_link3.abandon_date, None)
        self.assertEqual(created_link3.description, None)
        self.assertTrue(created_link3.notes.startswith("Automatically imported from UISP on"))

        self.assertIsNone(Link.objects.filter(uisp_id="uisp-uuid4").first())

        self.assertEqual(created_link5.from_device, self.device1)
        self.assertEqual(created_link5.to_device, self.device4)
        self.assertEqual(created_link5.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(created_link5.type, Link.LinkType.ETHERNET)
        self.assertEqual(created_link5.install_date, None)
        self.assertEqual(created_link5.abandon_date, None)
        self.assertEqual(created_link5.description, None)
        self.assertTrue(created_link5.notes.startswith("Automatically imported from UISP on"))

    @patch("meshapi.util.uisp_import.sync_handlers.get_uisp_session")
    @patch("meshapi.util.uisp_import.sync_handlers.notify_admins_of_changes")
    @patch("meshapi.util.uisp_import.update_objects.get_uisp_link_last_seen")
    def test_import_and_sync_links_uisp_mismatch_and_duplicate(
        self, mock_get_uisp_last_seen, mock_notify_admins, mock_get_uisp_session
    ):
        mock_get_uisp_session.return_value = "mock_uisp_session"
        mock_get_uisp_last_seen.return_value = datetime.datetime.now()

        self.link1.delete()
        self.link2.delete()
        self.link3.delete()

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
                            "id": "uisp-uuid6",
                            "category": "wireless",
                            "name": "nycmesh-7890-dev6",
                        }
                    }
                },
                "state": "active",
                "id": "uisp-uuid40b",
                "type": "ethernet",
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
                            "id": "uisp-uuid6",
                            "category": "wireless",
                            "name": "nycmesh-7890-dev6",
                        }
                    }
                },
                "state": "active",
                "id": "uisp-uuid50b",
                "type": "ethernet",
            },
            {
                "from": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid3",
                            "category": "wireless",
                            "name": "nycmesh-9012-dev3",
                        }
                    }
                },
                "to": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid6",
                            "category": "wireless",
                            "name": "nycmesh-7890-dev6",
                        }
                    }
                },
                "state": "active",
                "id": "uisp-uuid60a",
                "type": "ethernet",
            },
            {
                "from": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid3",
                            "category": "wireless",
                            "name": "nycmesh-9012-dev3",
                        }
                    }
                },
                "to": {
                    "device": {
                        "identification": {
                            "id": "uisp-uuid6",
                            "category": "wireless",
                            "name": "nycmesh-7890-dev6",
                        }
                    }
                },
                "state": "active",
                "id": "uisp-uuid60b",
                "type": "ethernet",
            },
        ]

        import_and_sync_uisp_links(uisp_links)

        self.link4.refresh_from_db()
        self.link5a.refresh_from_db()
        self.link5b.refresh_from_db()
        self.link6a.refresh_from_db()
        self.link6b.refresh_from_db()

        self.assertEqual(self.link4.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(self.link4.uisp_id, "uisp-uuid40b")

        self.assertEqual(self.link5a.status, Link.LinkStatus.INACTIVE)
        self.assertEqual(self.link5a.uisp_id, "uisp-uuid50a")
        self.assertEqual(self.link5b.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(self.link5b.uisp_id, "uisp-uuid50b")

        self.assertEqual(self.link6a.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(self.link6a.uisp_id, "uisp-uuid60a")
        self.assertEqual(self.link6b.status, Link.LinkStatus.ACTIVE)
        self.assertEqual(self.link6b.uisp_id, "uisp-uuid60b")

        self.assertEqual(len(Link.objects.all()), 5)

        mock_notify_admins.assert_has_calls(
            [
                call(self.link4, ["Changed UISP link ID to uisp-uuid40b"]),
                call(self.link5b, ["Marked as Active due to it coming back online in UISP"]),
                call(
                    self.link5a,
                    [
                        "Marked as inactive because there is no corresponding link in UISP, it was probably deleted there"
                    ],
                ),
            ]
        )

    @patch("meshapi.util.uisp_import.sync_handlers.get_uisp_session")
    @patch("meshapi.util.uisp_import.sync_handlers.notify_admins_of_changes")
    @patch("meshapi.util.uisp_import.sync_handlers.update_link_from_uisp_data")
    @patch("meshapi.util.uisp_import.sync_handlers.notify_administrators_of_data_issue")
    def test_duplicate_uisp_id_links(
        self,
        mock_notify_administrators_of_data_issue,
        mock_update_link,
        mock_notify_admins_of_changes,
        mock_get_uisp_session,
    ):
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
                "id": "uisp-uuid12345",
                "type": "wireless",
                "frequency": 5_000,
            },
        ]

        dup_link_1 = Link(
            id=uuid.UUID("6a86c400-550d-489b-86d5-106fd95ae1e6"),
            from_device=self.device1,
            to_device=self.device2,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIVE_GHZ,
            uisp_id="uisp-uuid12345",
        )
        dup_link_1.save()

        dup_link_2 = Link(
            id=uuid.UUID("ed6f24b6-8b1d-4650-9f1d-471c25828935"),
            from_device=self.device1,
            to_device=self.device2,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIVE_GHZ,
            uisp_id="uisp-uuid12345",
        )
        dup_link_2.save()

        import_and_sync_uisp_links(uisp_links)

        mock_update_link.assert_has_calls([])
        mock_notify_admins_of_changes.assert_has_calls([])
        mock_notify_administrators_of_data_issue.assert_called_once_with(
            [dup_link_1, dup_link_2],
            LinkSerializer,
            message="Possible duplicate objects detected, links share the same UISP ID (uisp-uuid12345)",
        )

        self.assertEqual(2, Link.objects.filter(uisp_id="uisp-uuid12345").count())

    @patch("meshapi.util.uisp_import.sync_handlers.get_uisp_session")
    @patch("meshapi.util.uisp_import.sync_handlers.notify_admins_of_changes")
    @patch("meshapi.util.uisp_import.sync_handlers.update_link_from_uisp_data")
    def test_import_and_sync_invalid_uisp_links(self, mock_update_link, mock_notify_admins, mock_get_uisp_session):
        mock_get_uisp_session.return_value = "mock_uisp_session"

        uisp_links = [
            {
                "from": {"device": None},
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
                "to": {"device": None},
                "state": "inactive",
                "id": "uisp-uuid2",
                "type": "wireless",
                "frequency": 60_000,
            },
        ]

        import_and_sync_uisp_links(uisp_links)

        mock_update_link.assert_has_calls([])
        mock_notify_admins.assert_has_calls([])

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
        self.assertEqual(new_los.notes, f"Created automatically from Link ID {self.link2.id} (NN1234 ↔ NN9012)\n\n")

    def test_sync_same_building_link_with_los(self):
        self.device3b = Device(
            node=self.node3,
            status=Device.DeviceStatus.ACTIVE,
            name="nycmesh-9012-dev3b",
        )
        self.device3b.save()

        # Clear out the existing links so the only LOS is a building self-loop
        self.link1.delete()
        self.link2.delete()
        self.link3.delete()

        link = Link(
            from_device=self.device3,
            to_device=self.device3b,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIVE_GHZ,
        )
        link.save()

        sync_link_table_into_los_objects()

        self.assertEqual(0, len(LOS.objects.all()))

    def test_sync_missing_building_link_with_los(self):
        # Clear out the existing links and a building so the only link is one
        # that's missing a building on one side
        self.link2.delete()
        self.building2.delete()

        sync_link_table_into_los_objects()

        self.assertEqual(0, len(LOS.objects.all()))

    def test_sync_fiber_link(self):
        self.link1.type = Link.LinkType.FIBER
        self.link1.save()
        self.link2.type = Link.LinkType.ETHERNET
        self.link2.save()
        self.link3.type = Link.LinkType.ETHERNET
        self.link3.save()

        link3 = Link(
            from_device=self.device2,
            to_device=self.device3,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.VPN,
            uisp_id="uisp-uuid3",
        )
        link3.save()

        sync_link_table_into_los_objects()

        # Fiber, ethernet, and VPN links should not generate LOS entries
        self.assertEqual(0, len(LOS.objects.all()))

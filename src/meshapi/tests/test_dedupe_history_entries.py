from datetime import datetime, date, timezone
from django.core import management
from uuid import UUID
from django.test import TestCase
from simple_history.models import HistoricalRecords

from meshapi.models.devices.device import Device
from meshapi.models.link import Link
from meshapi.models.node import Node


class TestDedupeHistoryEntries(TestCase):
    def setUp(self) -> None:
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
        # Save the device multiple times to see if we can get some bad history
        self.device3.save()
        self.device3.save()
        self.device3.save()

        self.link = Link(
            from_device=self.device1,
            to_device=self.device2,
            status=Link.LinkStatus.ACTIVE,
            type=Link.LinkType.FIVE_GHZ,
            uisp_id="fake-uisp-uuid",
        )

        # Save the link multiple times to see if we can get some bad history
        self.link.save()
        self.link.save()
        self.link.save()
        self.link.save()


    def test_deduplicate_history(self):
        # Ensure link has 4 entries
        self.assertEqual(4, len(self.link.history.all()))

        # Ensure device3 has 3
        self.assertEqual(3, len(self.device3.history.all()))

        # etc
        self.assertEqual(1, len(self.device2.history.all()))

        management.call_command("dedupe_history_entries")
        self.assertEqual(1, len(self.link.history.all()))
        self.assertEqual(1, len(self.device3.history.all()))
        self.assertEqual(1, len(self.device2.history.all()))
        


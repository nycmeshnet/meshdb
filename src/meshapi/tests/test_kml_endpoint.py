import datetime
import json

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from fastkml import kml
from lxml import etree
from rest_framework.authtoken.models import Token

from meshapi.models import Building, Device, Install, Link, Member, Sector

import random
random.seed()


def create_building_install_pair(member_ref, nn, building_status=Building.BuildingStatus.ACTIVE):
    building = Building(
        building_status=building_status,
        address_truth_sources="",
        latitude=0,
        longitude=0,
        altitude=0,
        primary_nn=nn,
    )
    building.save()

    install = Install(
        member=member_ref,
        building=building,
        install_number=nn,
        status=Install.InstallStatus.ACTIVE,
        request_date=datetime.date.today(),
    )
    install.save()

    device = Device(
        status=Device.DeviceStatus.ACTIVE,
        name=f"device-{nn}",
        device_name="LBE",
        serves_install=install,
        powered_by_install=install,
        network_number=nn #random.randrange(3000, 7999) # Seems high enough lol
    )
    device.save()

    return install, building, device


class TestKMLEndpoint(TestCase):
    c = Client()

    def test_views_get_unauthenticated(self):
        routes = [
            ("/api/v1/geography/whole-mesh.kml", 200),
        ]

        for route, code in routes:
            response = self.c.get(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for GET {route}. Should be {code}, but got {response.status_code}",
            )

            response = self.c.options(route)
            self.assertEqual(
                code,
                response.status_code,
                f"status code incorrect for OPTIONS {route}. Should be {code}, but got {response.status_code}",
            )

    def test_kml_data(self):
        links = []

        fake_member = Member(name="Stacy Fakename")
        fake_member.save()

        grand_install, grand, grand_dev = create_building_install_pair(fake_member, 1934)
        sn1_install, sn1, sn1_dev = create_building_install_pair(fake_member, 227)
        sn10_install, sn10, sn10_dev = create_building_install_pair(fake_member, 10)
        sn3_install, sn3, sn3_dev = create_building_install_pair(fake_member, 713)
        brian_install, brian, brian_dev = create_building_install_pair(fake_member, 3)
        random_install, random, random_dev, = create_building_install_pair(fake_member, 123)

        links.append(
            Link(
                from_device=sn1_dev,
                to_device=sn3_dev,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.VPN,
                install_date=datetime.date(2022, 1, 26),
            )
        )

        links.append(
            Link(
                from_device=sn1_dev,
                to_device=grand_dev,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.MMWAVE,
            )
        )

        links.append(
            Link(
                from_device=sn1_dev,
                to_device=brian_dev,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.STANDARD,
            )
        )

        links.append(
            Link(
                from_device=grand_dev,
                to_device=sn10_dev,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIBER,
            )
        )

        links.append(
            Link(
                from_device=grand_dev,
                to_device=random_dev,
                status=Link.LinkStatus.PLANNED,
                type=Link.LinkType.STANDARD,
            )
        )

        for link in links:
            link.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/geography/whole-mesh.kml")

        kml_tree = etree.fromstring(response.content.decode("UTF8"))

        # TODO: Actually assert real things here in a less brittle way,
        #  once fastkml is actually capable of parsing its own outputs
        assert len(kml_tree[0]) == 6  # 4 styles and 2 folders
        assert len(kml_tree[0][4]) == 7  # 5 borough folders and "Other" + 1 for "name" tag
        assert len(kml_tree[0][4][6]) == 7  # 6 nodes, all in the "Other" folder + 1 for "name" tag
        assert len(kml_tree[0][5]) == 6  # 5 links + 1 for "name" tag

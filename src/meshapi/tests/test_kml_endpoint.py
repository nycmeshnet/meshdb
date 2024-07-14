import datetime

from django.test import Client, TestCase
from lxml import etree

from meshapi.models import Building, Device, Install, Link, Member, Node


def create_building_install_node_and_device(member_ref, nn):
    node = Node(
        network_number=nn,
        status=Node.NodeStatus.ACTIVE,
        latitude=0,
        longitude=0,
    )
    node.save()

    building = Building(
        address_truth_sources=[],
        latitude=0,
        longitude=0,
        altitude=0,
        primary_node=node,
    )
    building.save()

    install = Install(
        member=member_ref,
        building=building,
        node=node,
        status=Install.InstallStatus.ACTIVE,
        request_date=datetime.date.today(),
    )
    install.save()

    device = Device(
        node=node,
        model="OmniTik",
        type=Device.DeviceType.ROUTER,
        status=Device.DeviceStatus.ACTIVE,
        latitude=0,
        longitude=0,
    )
    device.save()

    return building, install, node, device


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

        grand_building, grand_install, grand, grand_omni = create_building_install_node_and_device(fake_member, 1934)
        sn1_building, sn1_install, sn1, sn1_omni = create_building_install_node_and_device(fake_member, 227)
        sn1_building, sn10_install, sn10, sn10_omni = create_building_install_node_and_device(fake_member, 10)
        s3_building, sn3_install, sn3, sn3_omni = create_building_install_node_and_device(fake_member, 713)
        brian_building, brian_install, brian, brian_omni = create_building_install_node_and_device(fake_member, 3)
        random_building, random_install, random, random_omni = create_building_install_node_and_device(fake_member, 123)
        dead_building, dead_install, dead, dead_omni = create_building_install_node_and_device(fake_member, 888)
        dead_omni.status = Device.DeviceStatus.INACTIVE
        dead_omni.save()

        links.append(
            Link(
                from_device=sn1_omni,
                to_device=sn3_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.VPN,
                install_date=datetime.date(2022, 1, 26),
            )
        )

        links.append(
            Link(
                from_device=sn1_omni,
                to_device=grand_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.SIXTY_GHZ,
            )
        )

        links.append(
            Link(
                from_device=sn1_omni,
                to_device=brian_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
            )
        )

        links.append(
            Link(
                from_device=grand_omni,
                to_device=sn10_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIBER,
            )
        )

        links.append(
            Link(
                from_device=grand_omni,
                to_device=random_omni,
                status=Link.LinkStatus.PLANNED,
                type=Link.LinkType.FIVE_GHZ,
            )
        )

        # Should show up as inactive because dead_omni is inactive
        links.append(
            Link(
                from_device=dead_omni,
                to_device=random_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
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
        assert len(kml_tree[0][4]) == 3  # "Active" and "Inactive" node folders + 1 for "name" tag
        assert len(kml_tree[0][4][1]) == 7  # 5 borough folders and "Other" + 1 for "name" tag
        assert len(kml_tree[0][4][1][6]) == 15  # 7 installs and 7 NNs, all in the "Other" folder + 1 for "name" tag
        assert len(kml_tree[0][5]) == 3  # "Active" and "Inactive" link folders + 1 for "name" tag
        assert len(kml_tree[0][5][1]) == 5  # 4 active links + 1 for "name" tag
        assert len(kml_tree[0][5][2]) == 3  # 1 inactive links + 1 for "name" tag

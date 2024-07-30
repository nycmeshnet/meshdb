import datetime

from django.test import Client, TestCase
from fastkml import kml

from meshapi.models import LOS, Building, Device, Install, Link, Member, Node


def create_building_install_node_and_device(member_ref, nn, install_number=None):
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
        install_number=install_number if install_number else nn,
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
        sn10_building, sn10_install, sn10, sn10_omni = create_building_install_node_and_device(fake_member, 10)
        sn3_building, sn3_install, sn3, sn3_omni = create_building_install_node_and_device(fake_member, 713)
        brian_building, brian_install, brian, brian_omni = create_building_install_node_and_device(fake_member, 3)
        modern_hub_building, modern_hub_install, modern_hub, modern_hub_omni = create_building_install_node_and_device(
            fake_member, 431, 14412
        )
        random_building, random_install, random, random_omni = create_building_install_node_and_device(fake_member, 123)
        dead_building, dead_install, dead, dead_omni = create_building_install_node_and_device(fake_member, 888)
        dead_omni.status = Device.DeviceStatus.INACTIVE
        dead_omni.save()

        # VPN Links should be hidden on the KML map
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

        # Should show up as active even though dead_omni is inactive (for consistency with the map)
        links.append(
            Link(
                from_device=dead_omni,
                to_device=random_omni,
                status=Link.LinkStatus.ACTIVE,
                type=Link.LinkType.FIVE_GHZ,
            )
        )

        los1 = LOS(
            from_building=grand_building,
            to_building=sn3_building,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=datetime.date(2022, 1, 26),
        )
        los1.save()

        los_duplicate = LOS(
            from_building=grand_building,
            to_building=sn3_building,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=datetime.date(2022, 1, 26),
        )
        los_duplicate.save()

        link_duplicate_los = LOS(
            from_building=grand_building,
            to_building=sn10_building,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=datetime.date(2022, 1, 26),
        )
        link_duplicate_los.save()

        building_no_installs = Building(
            latitude=0,
            longitude=0,
            address_truth_sources=[],
        )
        building_no_installs.save()

        los_no_installs = LOS(
            from_building=grand_building,
            to_building=building_no_installs,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=datetime.date(2022, 1, 26),
        )
        los_no_installs.save()

        self_loop_los = LOS(
            from_building=grand_building,
            to_building=grand_building,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=datetime.date(2022, 1, 26),
        )
        self_loop_los.save()

        los_modern_hub = LOS(
            from_building=grand_building,
            to_building=modern_hub_building,
            source=LOS.LOSSource.EXISTING_LINK,
            analysis_date=datetime.date(2022, 1, 26),
        )
        los_modern_hub.save()

        for link in links:
            link.save()

        self.maxDiff = None
        response = self.c.get("/api/v1/geography/whole-mesh.kml")

        kml_doc = kml.KML.class_from_string(response.content.decode("UTF8")).features[0]

        self.assertEqual(len(kml_doc.styles), 4)
        self.assertEqual(len(kml_doc.features), 2)

        nodes_folder = kml_doc.features[0]
        links_folder = kml_doc.features[1]

        self.assertEqual(nodes_folder.name, "Nodes")
        self.assertEqual(len(nodes_folder.features), 2)
        self.assertEqual(links_folder.name, "Links")
        self.assertEqual(len(links_folder.features), 2)

        active_nodes = nodes_folder.features[0]
        inactive_nodes = nodes_folder.features[1]
        active_links = links_folder.features[0]
        inactive_links = links_folder.features[1]

        self.assertEqual(active_nodes.name, "Active")
        self.assertEqual(inactive_nodes.name, "Inactive")
        self.assertEqual(active_links.name, "Active")
        self.assertEqual(inactive_links.name, "Inactive")

        self.assertEqual(len(active_nodes.features), 6)  # 5 Borough folders + "Other"
        self.assertEqual(len(inactive_nodes.features), 6)  # 5 Borough folders + "Other"

        active_nodes_other = active_nodes.features[5]
        self.assertEqual(len(active_nodes_other.features), 16)  # 8 installs and 8 NNs

        self.assertEqual(len(active_links.features), 4)
        self.assertEqual(len(inactive_links.features), 3)  # 1 inactive link + 2 LOSes

"""Tests for the ActiveMeshKML endpoint and its helper functions."""

import datetime
from unittest.mock import patch

from django.test import Client, RequestFactory, TestCase
from fastkml import kml

from meshapi.models import Building, Device, Install, Link, Member, Node
from meshapi.views.active_mesh_kml import (
    DOT_FALLBACK_URL,
    LINK_TYPE_COLORS,
    ActiveMeshKML,
    absolute_static_url,
    get_kml_link_type,
    hex_to_kml_color,
    link_type_to_style_id,
)

# Helpers


def _make_node(nn: int, status=Node.NodeStatus.ACTIVE, node_type=Node.NodeType.STANDARD, lat=40.7, lon=-73.9, alt=20):
    node = Node(network_number=nn, status=status, type=node_type, latitude=lat, longitude=lon, altitude=alt)
    node.save()
    return node


def _make_building(lat=40.7, lon=-73.9, alt=15):
    building = Building(address_truth_sources=[], latitude=lat, longitude=lon, altitude=alt)
    building.save()
    return building


def _make_install(member, building, node=None, status=Install.InstallStatus.ACTIVE, **kwargs):
    install = Install(
        member=member,
        building=building,
        node=node,
        status=status,
        request_date=datetime.datetime.now(datetime.timezone.utc),
        **kwargs,
    )
    install.save()
    return install


def _make_device(node, status=Device.DeviceStatus.ACTIVE):
    device = Device(node=node, status=status)
    device.save()
    return device


def _make_link(
    from_device,
    to_device,
    status=Link.LinkStatus.ACTIVE,
    link_type=Link.LinkType.FIVE_GHZ_UNSPECIFIED,
    install_date=None,
):
    link = Link(from_device=from_device, to_device=to_device, status=status, type=link_type, install_date=install_date)
    link.save()
    return link


def _parse_kml(response) -> kml.Document:
    """Return the top-level Document from a KML response."""
    return kml.KML.from_string(response.content.decode("UTF-8")).features[0]


# Utility function tests


class TestHelpers(TestCase):
    """Tests for hex_to_kml_color, link_type_to_style_id, get_kml_link_type, absolute_static_url."""

    def test_hex_to_kml_color(self):
        self.assertEqual(hex_to_kml_color("#FF0000"), "ff0000FF")
        self.assertEqual(hex_to_kml_color("#FF0000", alpha=128), "800000FF")

    def test_link_type_to_style_id(self):
        self.assertEqual(link_type_to_style_id("70-80 GHz"), "70_80_GHz_line")

    def test_get_kml_link_type_wds(self):
        dev1 = _make_device(_make_node(7901, lat=40.71, lon=-73.91))
        dev2 = _make_device(_make_node(7902, lat=40.72, lon=-73.92))
        link = Link(from_device=dev1, to_device=dev2, type=Link.LinkType.FIVE_GHZ_WDS)
        self.assertEqual(get_kml_link_type(link), "WDS (5 GHz)")

    def test_get_kml_link_type_five_ghz_grouping(self):
        dev1 = _make_device(_make_node(7903, lat=40.71, lon=-73.91))
        dev2 = _make_device(_make_node(7904, lat=40.72, lon=-73.92))
        for lt in [Link.LinkType.FIVE_GHZ_UNSPECIFIED, Link.LinkType.FIVE_GHZ_AIRMAX, Link.LinkType.FIVE_GHZ_WLAN]:
            link = Link(from_device=dev1, to_device=dev2, type=lt)
            self.assertEqual(get_kml_link_type(link), "5 GHz")

    def test_get_kml_link_type_passthrough(self):
        dev1 = _make_device(_make_node(7905, lat=40.71, lon=-73.91))
        dev2 = _make_device(_make_node(7906, lat=40.72, lon=-73.92))
        self.assertEqual(get_kml_link_type(Link(from_device=dev1, to_device=dev2, type=Link.LinkType.FIBER)), "Fiber")
        self.assertEqual(get_kml_link_type(Link(from_device=dev1, to_device=dev2, type=None)), "Other")

    def test_absolute_static_url(self):
        factory = RequestFactory()
        request = factory.get("/api/v1/geography/active-mesh.kml", SERVER_NAME="meshdb.example.com", SERVER_PORT="443")

        with patch("meshapi.views.active_mesh_kml.KML_ICON_URL", "https://cdn.example.com/icon.png"):
            self.assertEqual(
                absolute_static_url(request, "meshapi/kml-icons/dot-100.png"), "https://cdn.example.com/icon.png"
            )

        with patch("meshapi.views.active_mesh_kml.KML_ICON_URL", None):
            with patch("meshapi.views.active_mesh_kml.KML_ICON_BASE_URL", "https://meshdb.example.com"):
                self.assertIn(
                    "https://meshdb.example.com", absolute_static_url(request, "meshapi/kml-icons/dot-100.png")
                )

        with patch("meshapi.views.active_mesh_kml.KML_ICON_URL", None):
            with patch("meshapi.views.active_mesh_kml.KML_ICON_BASE_URL", None):
                with patch("meshapi.views.active_mesh_kml.static", side_effect=Exception("broken")):
                    self.assertEqual(absolute_static_url(request, "meshapi/kml-icons/dot-100.png"), DOT_FALLBACK_URL)


# Endpoint tests


class TestActiveMeshKMLEndpoint(TestCase):
    """Tests for the ActiveMeshKML endpoint: structure, nodes, links, and edge cases."""

    c = Client()

    def test_empty_db_returns_valid_kml(self):
        response = self.c.get("/api/v1/geography/active-mesh.kml")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(kml.KML.from_string(response.content.decode("UTF-8")))

    def test_kml_has_lookat_element(self):
        response = self.c.get("/api/v1/geography/active-mesh.kml")
        content = response.content.decode("UTF-8")
        self.assertIn("<LookAt>", content)
        self.assertIn("<longitude>-73.9857</longitude>", content)

    def test_folder_structure(self):
        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        folder_names = [f.name for f in doc.features]
        self.assertIn("Nodes", folder_names)
        self.assertIn("Links", folder_names)

        nodes_folder = next(f for f in doc.features if f.name == "Nodes")
        subfolder_names = [f.name for f in nodes_folder.features]
        for expected in [
            "Standard Nodes",
            "Hub Nodes",
            "Supernode Nodes",
            "POP Nodes",
            "AP Nodes",
            "Remote Nodes",
            "Planned Nodes",
        ]:
            self.assertIn(expected, subfolder_names)

    def test_all_styles_present(self):
        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        style_ids = {s.id for s in doc.styles}
        for expected in [
            "red_dot",
            "blue_dot",
            "hub_dot",
            "green_dot",
            "yellow_dot",
            "purple_dot",
            "white_dot",
            "white_line",
        ]:
            self.assertIn(expected, style_ids)
        for link_type in LINK_TYPE_COLORS:
            self.assertIn(link_type_to_style_id(link_type), style_ids)

    def test_node_types_appear_in_correct_folders(self):
        """Standard, Hub, and Supernode nodes should each appear in their type folder."""
        member = Member(name="Test Member")
        member.save()

        for nn, nt, folder_name in [
            (100, Node.NodeType.STANDARD, "Standard Nodes"),
            (200, Node.NodeType.HUB, "Hub Nodes"),
            (300, Node.NodeType.SUPERNODE, "Supernode Nodes"),
        ]:
            node = _make_node(nn, node_type=nt)
            building = _make_building(lat=node.latitude, lon=node.longitude)
            _make_install(member, building, node, status=Install.InstallStatus.ACTIVE)

            response = self.c.get("/api/v1/geography/active-mesh.kml")
            doc = _parse_kml(response)
            nodes_folder = next(f for f in doc.features if f.name == "Nodes")
            folder = next(f for f in nodes_folder.features if f.name == folder_name)
            placemark_names = [p.name for p in folder.features]
            self.assertIn(str(nn), placemark_names)

    def test_pending_install_in_planned_folder(self):
        """A pending install (no active installs at location) goes to Planned Nodes folder."""
        member = Member(name="Test Member")
        member.save()
        node = _make_node(700, status=Node.NodeStatus.PLANNED, node_type=Node.NodeType.STANDARD)
        building = _make_building(lat=node.latitude, lon=node.longitude)
        _make_install(member, building, node, status=Install.InstallStatus.PENDING)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        nodes_folder = next(f for f in doc.features if f.name == "Nodes")
        planned_folder = next(f for f in nodes_folder.features if f.name == "Planned Nodes")
        placemark_names = [p.name for p in planned_folder.features]
        self.assertIn("700", placemark_names)

    def test_pending_with_active_goes_to_type_folder(self):
        """If any install at a location is active, it goes to the type folder, not Planned."""
        member = Member(name="Test Member")
        member.save()
        node = _make_node(800, status=Node.NodeStatus.ACTIVE, node_type=Node.NodeType.STANDARD)
        building = _make_building(lat=node.latitude, lon=node.longitude)
        _make_install(member, building, node, status=Install.InstallStatus.ACTIVE)
        _make_install(member, building, node, status=Install.InstallStatus.PENDING)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        nodes_folder = next(f for f in doc.features if f.name == "Nodes")
        standard_folder = next(f for f in nodes_folder.features if f.name == "Standard Nodes")
        placemark_names = [p.name for p in standard_folder.features]
        self.assertIn("800", placemark_names)

    def test_inactive_install_not_shown(self):
        """Inactive installs should not appear in the KML at all."""
        member = Member(name="Test Member")
        member.save()
        node = _make_node(900, status=Node.NodeStatus.INACTIVE)
        building = _make_building(lat=node.latitude, lon=node.longitude)
        _make_install(member, building, node, status=Install.InstallStatus.INACTIVE)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        self.assertNotIn(">900<", response.content.decode("UTF-8"))

    def test_multiple_installs_same_location_grouped(self):
        """Multiple installs at the same node should produce one placemark."""
        member = Member(name="Test Member")
        member.save()
        node = _make_node(1000, lat=40.75, lon=-73.95)
        building = _make_building(lat=40.75, lon=-73.95)
        _make_install(member, building, node, status=Install.InstallStatus.ACTIVE)
        _make_install(member, building, node, status=Install.InstallStatus.ACTIVE)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        nodes_folder = next(f for f in doc.features if f.name == "Nodes")
        standard_folder = next(f for f in nodes_folder.features if f.name == "Standard Nodes")
        nn_placemarks = [p for p in standard_folder.features if p.name == "1000"]
        self.assertEqual(len(nn_placemarks), 1)

    def test_install_without_node_uses_install_number(self):
        """Install without a node should show with install number identifier."""
        member = Member(name="Test Member")
        member.save()
        building = _make_building(lat=40.76, lon=-73.96)
        install = _make_install(member, building, node=None, status=Install.InstallStatus.ACTIVE)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        self.assertIn(f"#{install.install_number}", response.content.decode("UTF-8"))

    def test_node_without_installs_still_shown(self):
        """An active node with coordinates but no installs should still appear."""
        _make_node(1100, lat=40.77, lon=-73.97, node_type=Node.NodeType.STANDARD)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        self.assertIn(">1100<", response.content.decode("UTF-8"))

    def test_planned_node_without_installs(self):
        """A planned node with no installs should appear in Planned Nodes folder."""
        _make_node(1200, status=Node.NodeStatus.PLANNED, lat=40.78, lon=-73.98)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        nodes_folder = next(f for f in doc.features if f.name == "Nodes")
        planned_folder = next(f for f in nodes_folder.features if f.name == "Planned Nodes")
        placemark_names = [p.name for p in planned_folder.features]
        self.assertIn("1200", placemark_names)

    def test_node_with_name_in_extended_data(self):
        """A node with a colloquial name should have it in extended data."""
        member = Member(name="Test Member")
        member.save()
        node = _make_node(1300, node_type=Node.NodeType.SUPERNODE)
        node.name = "Grand St"
        node.save()
        building = _make_building(lat=node.latitude, lon=node.longitude)
        _make_install(member, building, node, status=Install.InstallStatus.ACTIVE)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        self.assertIn("Grand St", response.content.decode("UTF-8"))

    def test_install_date_from_earliest_active(self):
        """The earliest install_date among active installs should be in extended data."""
        member = Member(name="Test Member")
        member.save()
        node = _make_node(1400, lat=40.79, lon=-73.99)
        building = _make_building(lat=40.79, lon=-73.99)
        _make_install(
            member, building, node, status=Install.InstallStatus.ACTIVE, install_date=datetime.date(2023, 6, 15)
        )
        _make_install(
            member, building, node, status=Install.InstallStatus.ACTIVE, install_date=datetime.date(2022, 3, 10)
        )

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        self.assertIn("2022-03-10", response.content.decode("UTF-8"))

    def test_link_type_subfolders_exist(self):
        """Links folder should have subfolders for each link type + Planned."""
        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        links_folder = next(f for f in doc.features if f.name == "Links")
        subfolder_names = [f.name for f in links_folder.features]
        for link_type in LINK_TYPE_COLORS.keys():
            self.assertIn(link_type, subfolder_names)
        self.assertIn("Planned Links", subfolder_names)

    def test_active_link_in_correct_type_folder(self):
        """An active 60 GHz link should end up in the '60 GHz' folder."""
        member = Member(name="Link Test Member")
        member.save()
        node_a = _make_node(2001, lat=40.71, lon=-73.91, alt=30)
        node_b = _make_node(2002, lat=40.72, lon=-73.92, alt=25)
        dev_a = _make_device(node_a)
        dev_b = _make_device(node_b)
        building_a = _make_building(lat=40.71, lon=-73.91)
        building_b = _make_building(lat=40.72, lon=-73.92)
        _make_install(member, building_a, node_a)
        _make_install(member, building_b, node_b)
        _make_link(dev_a, dev_b, link_type=Link.LinkType.SIXTY_GHZ)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        links_folder = next(f for f in doc.features if f.name == "Links")
        sixty_folder = next(f for f in links_folder.features if f.name == "60 GHz")
        self.assertEqual(len(sixty_folder.features), 1)
        self.assertIn("2001", sixty_folder.features[0].name)
        self.assertIn("2002", sixty_folder.features[0].name)

    def test_vpn_links_excluded(self):
        """VPN links should not appear in the KML."""
        member = Member(name="Link Test Member")
        member.save()
        node_a = _make_node(2010, lat=40.71, lon=-73.91)
        node_b = _make_node(2011, lat=40.72, lon=-73.92)
        dev_a = _make_device(node_a)
        dev_b = _make_device(node_b)
        _make_link(dev_a, dev_b, link_type=Link.LinkType.VPN)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        links_folder = next(f for f in doc.features if f.name == "Links")
        self.assertEqual(sum(len(f.features) for f in links_folder.features), 0)

    def test_planned_link_in_planned_folder(self):
        """A Planned link should appear in the 'Planned Links' folder."""
        member = Member(name="Link Test Member")
        member.save()
        node_a = _make_node(2020, lat=40.71, lon=-73.91)
        node_b = _make_node(2021, lat=40.72, lon=-73.92)
        dev_a = _make_device(node_a)
        dev_b = _make_device(node_b)
        _make_link(dev_a, dev_b, status=Link.LinkStatus.PLANNED, link_type=Link.LinkType.FIVE_GHZ_UNSPECIFIED)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        links_folder = next(f for f in doc.features if f.name == "Links")
        planned_folder = next(f for f in links_folder.features if f.name == "Planned Links")
        self.assertEqual(len(planned_folder.features), 1)

    def test_self_loop_link_excluded(self):
        """Links from a node to itself should not appear."""
        member = Member(name="Link Test Member")
        member.save()
        node_a = _make_node(2030, lat=40.71, lon=-73.91)
        dev_a = _make_device(node_a)
        dev_a2 = _make_device(node_a)
        _make_link(dev_a, dev_a2, link_type=Link.LinkType.FIVE_GHZ_UNSPECIFIED)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        links_folder = next(f for f in doc.features if f.name == "Links")
        self.assertEqual(sum(len(f.features) for f in links_folder.features), 0)

    def test_inactive_links_excluded(self):
        """Inactive links should not appear."""
        member = Member(name="Link Test Member")
        member.save()
        node_a = _make_node(2040, lat=40.71, lon=-73.91)
        node_b = _make_node(2041, lat=40.72, lon=-73.92)
        dev_a = _make_device(node_a)
        dev_b = _make_device(node_b)
        _make_link(dev_a, dev_b, status=Link.LinkStatus.INACTIVE, link_type=Link.LinkType.FIBER)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        links_folder = next(f for f in doc.features if f.name == "Links")
        self.assertEqual(sum(len(f.features) for f in links_folder.features), 0)

    def test_link_with_install_date(self):
        """Link's install_date should be in extended data."""
        member = Member(name="Link Test Member")
        member.save()
        node_a = _make_node(2050, lat=40.71, lon=-73.91)
        node_b = _make_node(2051, lat=40.72, lon=-73.92)
        dev_a = _make_device(node_a)
        dev_b = _make_device(node_b)
        _make_link(dev_a, dev_b, link_type=Link.LinkType.FIBER, install_date=datetime.date(2023, 1, 15))

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        self.assertIn("2023-01-15", response.content.decode("UTF-8"))

    def test_fiber_wins_over_five_ghz(self):
        """When fiber and 5 GHz links exist between same nodes, only fiber should remain."""
        member = Member(name="Priority Test Member")
        member.save()
        node_a = _make_node(3001, lat=40.71, lon=-73.91, alt=30)
        node_b = _make_node(3002, lat=40.72, lon=-73.92, alt=25)
        dev_a = _make_device(node_a)
        dev_b = _make_device(node_b)
        dev_a2 = _make_device(node_a)
        dev_b2 = _make_device(node_b)
        building_a = _make_building(lat=40.71, lon=-73.91)
        building_b = _make_building(lat=40.72, lon=-73.92)
        _make_install(member, building_a, node_a)
        _make_install(member, building_b, node_b)
        _make_link(dev_a, dev_b, link_type=Link.LinkType.FIVE_GHZ_UNSPECIFIED)
        _make_link(dev_a2, dev_b2, link_type=Link.LinkType.FIBER)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        doc = _parse_kml(response)
        links_folder = next(f for f in doc.features if f.name == "Links")
        self.assertEqual(sum(len(f.features) for f in links_folder.features), 1)
        fiber_folder = next(f for f in links_folder.features if f.name == "Fiber")
        self.assertEqual(len(fiber_folder.features), 1)

    def test_prioritize_links_reverse_direction(self):
        """Links between the same pair of nodes but in opposite directions should still deduplicate."""
        view = ActiveMeshKML()
        coord_a = (-73.91, 40.71, 30.0)
        coord_b = (-73.92, 40.72, 25.0)

        kml_links = [
            {
                "link_label": "A<->B",
                "from_coord": coord_a,
                "to_coord": coord_b,
                "extended_data": {"type": "5 GHz", "from": "3001", "to": "3002"},
            },
            {
                "link_label": "B<->A",
                "from_coord": coord_b,
                "to_coord": coord_a,
                "extended_data": {"type": "Ethernet", "from": "3002", "to": "3001"},
            },
        ]

        result = view.prioritize_links(kml_links)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["extended_data"]["type"], "Ethernet")

    def test_null_altitude_uses_default(self):
        """When altitude is null, the DEFAULT_ALTITUDE (5m) should be used."""
        member = Member(name="Edge Case Member")
        member.save()
        node = _make_node(4002, lat=40.71, lon=-73.91, alt=None)
        building = _make_building(lat=40.71, lon=-73.91, alt=None)
        _make_install(member, building, node, status=Install.InstallStatus.ACTIVE)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        content = response.content.decode("UTF-8")
        self.assertIn(">4002<", content)
        self.assertIn("5.0", content)

    def test_node_coordinates_used_over_building_coordinates(self):
        """When a node has different coordinates than its building, node coords should be used."""
        member = Member(name="Edge Case Member")
        member.save()
        node = _make_node(4007, lat=40.80, lon=-73.80)
        building = _make_building(lat=40.71, lon=-73.91)
        _make_install(member, building, node, status=Install.InstallStatus.ACTIVE)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        content = response.content.decode("UTF-8")
        self.assertIn(">4007<", content)
        self.assertIn("-73.8", content)
        self.assertIn("40.8", content)

    def test_many_nodes_smoke_test(self):
        """Smoke test with many nodes to ensure no performance issues."""
        member = Member(name="Smoke Test Member")
        member.save()
        for i in range(500):
            node = _make_node(i + 1, lat=40.7 + i * 0.0005, lon=-73.9 + i * 0.0005)
            building = _make_building(lat=node.latitude, lon=node.longitude)
            _make_install(member, building, node, status=Install.InstallStatus.ACTIVE)

        response = self.c.get("/api/v1/geography/active-mesh.kml")
        self.assertEqual(response.status_code, 200)

from datetime import datetime
from typing import Collection, List

from django.db.models import Count, Exists, F, OuterRef, Prefetch, Q, Subquery

from meshapi.models import LOS, Device, Install, Link, Node, Sector
from meshapi.serializers import (
    ALLOWED_INSTALL_STATUSES,
    EXCLUDED_INSTALL_STATUSES,
    MapDataInstallSerializer,
    MapDataLinkSerializer,
    MapDataSectorSerializer,
)


def render_node_data() -> Collection[dict]:
    all_installs = []

    queryset = (
        Install.objects.select_related("building")
        .select_related("node")
        .prefetch_related("node__devices")
        .filter(~Q(status__in=EXCLUDED_INSTALL_STATUSES))
    )

    for install in queryset:
        all_installs.append(install)

    # We need to make sure there is an entry on the map for every NN, and since we excluded the
    # NN assigned rows in the query above, we need to go through the Node objects and
    # include the nns we haven't already covered via install num
    covered_nns = {install.install_number for install in all_installs}
    for node in (
        Node.objects.filter(~Q(status=Node.NodeStatus.INACTIVE) & Q(installs__status__in=ALLOWED_INSTALL_STATUSES))
        .prefetch_related("devices")
        .prefetch_related(
            Prefetch(
                "installs",
                queryset=Install.objects.all().select_related("building"),
                to_attr="prefetched_installs",
            )
        )
        .prefetch_related(
            Prefetch(
                "installs",
                queryset=Install.objects.filter(status=Install.InstallStatus.ACTIVE).select_related("building"),
                to_attr="active_installs",
            )
        )
    ):
        if node.network_number not in covered_nns:
            # Arbitrarily pick a representative install for the details of the "Fake" node,
            # preferring active installs if possible
            representative_install = (
                node.active_installs  # type: ignore[attr-defined]
                or node.prefetched_installs  # type: ignore[attr-defined]
            )[0]

            all_installs.append(
                Install(
                    install_number=node.network_number,
                    node=node,
                    status=Install.InstallStatus.NN_REASSIGNED
                    if node.status == node.NodeStatus.ACTIVE
                    else Install.InstallStatus.REQUEST_RECEIVED,
                    building=representative_install.building,
                    request_date=representative_install.request_date,
                    roof_access=representative_install.roof_access,
                ),
            )
            covered_nns.add(node.network_number)

    all_installs.sort(key=lambda i: i.install_number)

    all_installs_rendered_json = MapDataInstallSerializer(all_installs, many=True).data

    access_points = []
    for device in Device.objects.filter(
        Q(status=Device.DeviceStatus.ACTIVE) & (~Q(node__latitude=F("latitude")) | ~Q(node__longitude=F("longitude")))
    ):
        install_date = (
            int(
                datetime.combine(
                    device.install_date,
                    datetime.min.time(),
                ).timestamp()
                * 1000
            )
            if device.install_date
            else None
        )
        ap = {
            "id": 1_000_000 + device.id,  # Hacky but we have no choice
            "name": device.name,
            "status": "Installed",
            "coordinates": [device.longitude, device.latitude, None],
            "roofAccess": False,
            "notes": "AP",
            "panoramas": [],
        }

        if install_date:
            ap["requestDate"] = install_date
            ap["installDate"] = install_date

        access_points.append(ap)

    return all_installs_rendered_json + access_points


def render_link_data() -> Collection[dict]:
    all_links = []
    link_queryset = (
        Link.objects.exclude(status__in=[Link.LinkStatus.INACTIVE])
        .exclude(to_device__node__status=Node.NodeStatus.INACTIVE)
        .exclude(from_device__node__status=Node.NodeStatus.INACTIVE)
        .prefetch_related("to_device__node")
        .prefetch_related("from_device__node")
        .filter(
            # This horrible monster query exists to de-duplicate links between the same node pairs
            # so that the map doesn't freak out. These often exist because different devices on
            # the same nodes can be linked. This deduplication happens somewhat arbitrarily
            # and is borrowed from https://stackoverflow.com/a/69938289
            pk__in=Link.objects.values("from_device__node__network_number", "to_device__node__network_number")
            .distinct()
            .annotate(
                pk=Subquery(
                    Link.objects.filter(
                        from_device__node__network_number=OuterRef("from_device__node__network_number"),
                        to_device__node__network_number=OuterRef("to_device__node__network_number"),
                    )
                    .order_by("pk")
                    .values("pk")[:1]
                )
            )
            .values_list("pk", flat=True)
        )
        # TODO: Possibly re-enable the below filters? They make make the map arguably more accurate,
        #  but less consistent with the current one by removing links between devices that are
        #  inactive in UISP
        # .exclude(from_device__status=Device.DeviceStatus.INACTIVE)
        # .exclude(to_device__status=Device.DeviceStatus.INACTIVE)
    )

    db_links_rendered_json = MapDataLinkSerializer(link_queryset, many=True).data
    all_links.extend(db_links_rendered_json)

    covered_links = {(link["from"], link["to"]) for link in all_links}

    # Slightly hacky way to show ethernet cable runs on the old map.
    # We just look for nodes where there are installs on separate buildings
    # and add fake link objects to connect the installs on those other buildings to
    # the node dot
    cable_runs = []

    for node in (
        Node.objects.annotate(num_buildings=Count("buildings"))
        .filter(num_buildings__gt=1)
        .filter(~Q(status=Node.NodeStatus.INACTIVE) & Q(installs__status__in=ALLOWED_INSTALL_STATUSES))
        .prefetch_related(
            Prefetch(
                "buildings__installs",
                queryset=Install.objects.order_by("install_number").filter(status=Install.InstallStatus.ACTIVE),
                to_attr="active_installs",
            )
        )
    ):
        for building in node.buildings.all():
            active_installs = building.active_installs  # type: ignore[attr-defined]
            if active_installs:
                from_install = active_installs[0].install_number
                if from_install != node.network_number:
                    if (from_install, node.network_number) not in covered_links:
                        cable_runs.append(
                            {
                                "from": from_install,
                                "to": node.network_number,
                                "status": "active",
                            }
                        )

    all_links.extend(cable_runs)

    # Since the old school map has no concept of a LOS, only potential Links, we need to
    # create a fake potential Link object to represent each of our LOS entries
    # For our purposes here, we only care about LOS entries between buildings that have
    # install numbers. If one side of an LOS is a building that has no installs associated with
    # it, we exclude it
    los_objects_with_installs = (
        LOS.objects.filter(
            Exists(Install.objects.filter(building=OuterRef("from_building")))
            & Exists(Install.objects.filter(building=OuterRef("to_building")))
            & ~Q(from_building=F("to_building"))
        )
        .exclude(
            # Remove any LOS objects that would duplicate Link objects,
            # to avoid cluttering the map
            Exists(
                Link.objects.filter(
                    (
                        Q(from_device__node__buildings=OuterRef("from_building"))
                        & Q(to_device__node__buildings=OuterRef("to_building"))
                    )
                    | (
                        Q(from_device__node__buildings=OuterRef("to_building"))
                        & Q(to_device__node__buildings=OuterRef("from_building"))
                    )
                )
            )
        )
        .filter(
            # This horrible monster query exists to de-duplicate LOSes between the same building
            # pairs so that the map doesn't freak out. This deduplication happens somewhat
            # arbitrarily and is borrowed from https://stackoverflow.com/a/69938289
            pk__in=LOS.objects.values("from_building", "to_building")
            .distinct()
            .annotate(
                pk=Subquery(
                    LOS.objects.filter(
                        from_building=OuterRef("from_building"),
                        to_building=OuterRef("to_building"),
                    )
                    .order_by("pk")
                    .values("pk")[:1]
                )
            )
            .values_list("pk", flat=True)
        )
        .prefetch_related("from_building__installs")
        .prefetch_related("from_building__nodes")
        .prefetch_related("to_building__installs")
        .prefetch_related("to_building__nodes")
    )

    los_based_potential_links = []
    for los in los_objects_with_installs:
        from_numbers = set(i.install_number for i in los.from_building.installs.all()).union(
            set(n.network_number for n in los.from_building.nodes.all())
        )

        to_numbers = set(i.install_number for i in los.to_building.installs.all()).union(
            set(n.network_number for n in los.to_building.nodes.all())
        )

        for from_number in from_numbers:
            for to_number in to_numbers:
                los_based_potential_links.append(
                    {
                        "from": from_number,
                        "to": to_number,
                        "status": Link.LinkStatus.PLANNED.lower(),
                    }
                )

    all_links.extend(los_based_potential_links)

    return all_links


def render_sector_data() -> Collection[dict]:
    queryset = Sector.objects.filter(~Q(status__in=[Device.DeviceStatus.INACTIVE])).prefetch_related("node")
    return MapDataSectorSerializer(queryset, many=True).data

import logging
from typing import Optional

from meshapi import models
from meshapi.models import Node
from meshdb.utils.spreadsheet_import.csv_load import SpreadsheetRow


# This function is converted roughly from
# https://github.com/nycmeshnet/network-map/blob/a719fe14ff805a967a3d60e879e1f68ac99e4ce5/src/utils/index.js#L1
def get_node_type(notes: str) -> Node.NodeType.choices:
    lower_notes = notes.lower() if notes else None
    is_supernode = "supernode" in lower_notes if lower_notes else False
    is_pop = "pop" in lower_notes if lower_notes else False
    is_ap = "AP" in notes if notes else False
    is_hub = "hub" in lower_notes if lower_notes else False
    not_potential_hub = not notes or "hub?" not in lower_notes
    is_remote = "rem" in lower_notes if lower_notes else False

    if is_supernode:
        return Node.NodeType.SUPERNODE
    if is_pop:
        return Node.NodeType.POP
    if is_ap:
        return Node.NodeType.AP
    if is_hub and not_potential_hub:
        return Node.NodeType.HUB
    if is_remote:
        return Node.NodeType.REMOTE

    return Node.NodeType.STANDARD


def get_or_create_node(
    row: SpreadsheetRow,
) -> Optional[models.Node]:
    if not row.nn:
        # If this spreadsheet row doesn't have a network number,
        # there is no Node here to worry about
        return None

    existing_nodes = Node.objects.filter(network_number=row.nn)
    if len(existing_nodes):
        node = existing_nodes[0]

        if not node.name and row.nodeName:
            node.name = row.nodeName

        if not node.install_date or (row.installDate and row.installDate < node.install_date):
            node.install_date = row.installDate

        if not node.abandon_date or (row.abandonDate and row.abandonDate > node.abandon_date):
            # Set abandon date now, but it might get cleared later in the status-setting logic
            # (if there's another install connected to this node that is active)
            node.abandon_date = row.abandonDate

        if row.notes or row.notes2:
            node.notes += (
                f"Spreadsheet Notes (#{row.id}):\n"
                f"{row.notes if row.notes else None}\n\n"
                f"Spreadsheet Notes2 (#{row.id}):\n"
                f"{row.notes2 if row.notes2 else None}\n\n"
            )

        return node

    return Node(
        network_number=row.nn,
        name=row.nodeName if row.nodeName else None,
        # We use the spreadsheet lat/lon here, in case it has been adjusted manually, rather
        # than the values we got from parsing the address for the Building object
        latitude=row.latitude,
        longitude=row.longitude,
        altitude=row.altitude,
        install_date=row.installDate,
        # Set abandon date now, but it might get cleared later in the status-setting logic
        # (if there's another install connected to this node that is active)
        abandon_date=row.abandonDate,
        type=get_node_type(row.notes) if row.notes else Node.NodeType.STANDARD,
        notes=f"Spreadsheet Notes:\n"
        f"{row.notes if row.notes else None}\n\n"
        f"Spreadsheet Notes2:\n"
        f"{row.notes2 if row.notes2 else None}\n\n",
    )


def normalize_building_node_links(building: models.Building, node: models.Node):
    """
    Scan the node <-> building relations for the given node and building to make sure all buildings
     in the cluster refer to all nodes in the cluster and vice versa

     Also sets the correct primary_node pointer for each Building, by electing the oldest active node
     (or the oldest node if no active nodes exist)
    """
    buildings_in_cluster = {building}
    nodes_in_cluster = {node}

    # These loops will not correctly crawl deep or strange node <-> building
    # relationship structures but should be fine for simple flat clusters
    for n in building.nodes.all():
        for b in n.buildings.all():
            buildings_in_cluster.add(b)

    for b in node.buildings.all():
        for n in b.nodes.all():
            nodes_in_cluster.add(n)

    active_nodes = [node for node in nodes_in_cluster if node.status == node.NodeStatus.ACTIVE]

    primary_node = [
        node
        for node in sorted(
            active_nodes if active_nodes else nodes_in_cluster,
            key=lambda node: node.install_date,
        )
    ][0]

    for b in buildings_in_cluster:
        for n in nodes_in_cluster:
            b.nodes.add(n)

        b.primary_node = primary_node
        b.save()

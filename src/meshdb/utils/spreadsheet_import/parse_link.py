import datetime
import logging
import os
from typing import List, Optional

import django
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")
django.setup()


from meshapi import models
from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Node
from meshapi.util.uisp_import.fetch_uisp import get_uisp_device_detail, get_uisp_links, get_uisp_session
from meshapi.util.uisp_import.utils import get_building_from_network_number, get_link_type
from meshdb.utils.spreadsheet_import.csv_load import SpreadsheetLink, SpreadsheetLinkStatus, get_spreadsheet_links


def convert_spreadsheet_link_type(status: SpreadsheetLinkStatus, notes: Optional[str] = None) -> Link.LinkType:
    link_type = None
    if status in [
        SpreadsheetLinkStatus.active,
    ]:
        link_type = models.Link.LinkType.FIVE_GHZ
    elif status == SpreadsheetLinkStatus.vpn:
        link_type = models.Link.LinkType.VPN
    elif status == SpreadsheetLinkStatus.sixty_ghz:
        link_type = models.Link.LinkType.SIXTY_GHZ
    elif status == SpreadsheetLinkStatus.fiber:
        link_type = models.Link.LinkType.FIBER

    if notes and "siklu" in notes.lower():
        link_type = Link.LinkType.SEVENTY_EIGHTY_GHZ

    if notes and "24" in notes:
        link_type = Link.LinkType.TWENTYFOUR_GHZ

    return link_type


def convert_spreadsheet_link_status(status: SpreadsheetLinkStatus) -> Link.LinkStatus:
    if status in [
        SpreadsheetLinkStatus.vpn,
        SpreadsheetLinkStatus.active,
        SpreadsheetLinkStatus.sixty_ghz,
        SpreadsheetLinkStatus.fiber,
    ]:
        return models.Link.LinkStatus.ACTIVE
    elif status == SpreadsheetLinkStatus.dead:
        return models.Link.LinkStatus.INACTIVE
    elif status == SpreadsheetLinkStatus.planned:
        return models.Link.LinkStatus.PLANNED
    else:
        raise ValueError(f"Invalid spreadsheet link status {status}")


def get_node_from_spreadsheet_id(spreadsheet_node_id: int) -> Node:
    try:
        return Node.objects.get(network_number=spreadsheet_node_id)
    except Node.DoesNotExist:
        return Install.objects.get(install_number=spreadsheet_node_id).node


def get_building_from_spreadsheet_id(spreadsheet_node_id: int) -> Optional[Building]:
    try:
        # First, try to see if this is an NN, by checking for a node that matches
        node = Node.objects.get(network_number=spreadsheet_node_id)

        # If it's a node, use our logic for that
        return get_building_from_network_number(node.network_number)
    except Node.DoesNotExist:
        # If the spreadsheet node ID doesn't correspond to an NN, it must be an install number.
        # Just grab the building that corresponds to that install, easy
        try:
            return Install.objects.get(install_number=spreadsheet_node_id).building
        except Install.DoesNotExist:
            return None


def get_representative_device_for_node(node: Node, link_status: SpreadsheetLinkStatus) -> Device:
    if node is None:
        raise ValueError("Node must exist!")

    if not node.network_number:
        raise ValueError("Node must have a network_number!")

    search_terms = ["core", "omni"]

    # Look for a core router, and use that if available, if not, look for an omni
    for search_term in search_terms:
        candidates = node.devices.filter(name__icontains=search_term)
        if len(candidates):
            device = candidates.first()
            break
    else:
        # Otherwise return an arbitrary device
        device = node.devices.first()

    if not device:
        status = {
            Link.LinkStatus.ACTIVE: Device.DeviceStatus.ACTIVE,
            Link.LinkStatus.INACTIVE: Device.DeviceStatus.INACTIVE,
            Link.LinkStatus.PLANNED: Device.DeviceStatus.POTENTIAL,
        }[convert_spreadsheet_link_status(link_status)]

        logging.warning(f"Creating mock device for NN{node.network_number}. Could not find any pre-existing devices")
        device = Device(
            node=node,
            name=f"NN{node.network_number} Placeholder Device",
            status=status,
            notes=f"Automatically created to allow the import of spreadsheet links to/from NN{node.network_number}. "
            "Please check the links connected to this device, and connect them to a more accurate device at this node "
            "(you may need to create these other devices in MeshDB or UISP first)",
        )
        device.save()

    return device


def find_access_point_from_install_number(install_number: int) -> Optional[AccessPoint]:
    return AccessPoint.objects.filter(
        notes__contains=f"Automatically imported from Install #{install_number} in the spreadsheet"
    ).first()


def create_spreadsheet_link_notes(spreadsheet_link: SpreadsheetLink):
    notes = (
        f"Imported from spreadsheet link row "
        + f"{spreadsheet_link.from_node_id}->{spreadsheet_link.to_node_id} ({spreadsheet_link.status.value})\n"
        + "\n".join(
            s.strip()
            for s in [spreadsheet_link.where_to_where, spreadsheet_link.notes, spreadsheet_link.comments]
            if s.strip()
        )
    )

    if spreadsheet_link.install_date:
        notes += f"\nInstalled: {spreadsheet_link.install_date.isoformat()}"

    if spreadsheet_link.abandon_date:
        notes += f"\nAbandoned: {spreadsheet_link.abandon_date.isoformat()}"

    return notes


def create_link_for_device_pair(
    spreadsheet_link: SpreadsheetLink, from_device: Device, to_device: Device
) -> Optional[models.Link]:
    link_notes = "\n".join([spreadsheet_link.notes, spreadsheet_link.comments]).strip()
    link_type = convert_spreadsheet_link_type(spreadsheet_link.status, link_notes)

    link = models.Link(
        from_device=from_device,
        to_device=to_device,
        status=convert_spreadsheet_link_status(spreadsheet_link.status),
        type=link_type,
        install_date=spreadsheet_link.install_date,
        abandon_date=spreadsheet_link.abandon_date,
        description=spreadsheet_link.where_to_where if spreadsheet_link.where_to_where else None,
        notes=create_spreadsheet_link_notes(spreadsheet_link),
        uisp_id=None,
    )
    return link


def create_link(spreadsheet_link: SpreadsheetLink, from_node: Node, to_node: Node) -> Optional[models.Link]:
    from_device = get_representative_device_for_node(from_node, spreadsheet_link.status)
    to_device = get_representative_device_for_node(to_node, spreadsheet_link.status)

    return create_link_for_device_pair(spreadsheet_link, from_device, to_device)


def load_links_supplement_with_uisp(spreadsheet_links: List[SpreadsheetLink]):
    # Create LOS objects for the available data we have (UISP + the spreadsheet). To do this, we
    # first go through all the links in the spreadsheet and create the appropriate entries for them
    # then during UISP import we supplement this with any links not captured here
    for spreadsheet_link in spreadsheet_links:
        if spreadsheet_link.status in [SpreadsheetLinkStatus.vpn, SpreadsheetLinkStatus.fiber]:
            continue

        from_building = get_building_from_spreadsheet_id(spreadsheet_link.from_node_id)
        to_buidling = get_building_from_spreadsheet_id(spreadsheet_link.to_node_id)

        if not from_building or not to_buidling:
            logging.warning(
                f"Skipping link {spreadsheet_link.from_node_id} to {spreadsheet_link.to_node_id}. "
                f"Can't find one or more building objects for this entry"
            )
            continue

        if to_buidling == from_building:
            continue

        source = LOS.LOSSource.EXISTING_LINK
        if spreadsheet_link.status == SpreadsheetLinkStatus.planned:
            source = LOS.LOSSource.HUMAN_ANNOTATED

        analysis_date = spreadsheet_link.abandon_date
        if analysis_date is None and spreadsheet_link.status == SpreadsheetLinkStatus.dead:
            analysis_date = spreadsheet_link.install_date

        if analysis_date is None:
            analysis_date = datetime.date.today()

        existing_los = LOS.objects.filter(
            Q(from_building=from_building, to_building=to_buidling)
            | Q(from_building=to_buidling, to_building=from_building)
        ).first()
        if existing_los:
            continue

        los = LOS(
            from_building=from_building,
            to_building=to_buidling,
            source=source,
            analysis_date=analysis_date,
            notes=create_spreadsheet_link_notes(spreadsheet_link),
        )
        los.save()

    uisp_links = get_uisp_links()
    uisp_session = get_uisp_session()

    for uisp_link in uisp_links:
        try:
            if not uisp_link["from"]["device"]:
                continue

            from_device = Device.objects.get(uisp_id=uisp_link["from"]["device"]["identification"]["id"])
        except Device.DoesNotExist:
            if uisp_link["from"]["device"]["identification"]["category"] != "optical":
                logging.warning(
                    f"Skipping UISP link because device "
                    f"{uisp_link['from']['device']['identification']['name']} could not be found"
                )
            continue

        try:
            if not uisp_link["to"]["device"]:
                continue

            to_device = Device.objects.get(uisp_id=uisp_link["to"]["device"]["identification"]["id"])
        except Device.DoesNotExist:
            if uisp_link["to"]["device"]["identification"]["category"] != "optical":
                logging.warning(
                    f"Skipping UISP link because device "
                    f"{uisp_link['to']['device']['identification']['name']} could not be found"
                )
            continue

        # Create an LOS object if there are buildings that correspond to
        # the devices this link connects (there should be)
        from_building = get_building_from_network_number(from_device.node.network_number)
        to_buidling = get_building_from_network_number(to_device.node.network_number)
        if from_building and to_buidling and from_building != to_buidling:
            # First check to make sure we aren't duplicating a link from the spreadsheet
            if uisp_link["type"] not in ["ethernet", "pon"] and not len(
                LOS.objects.filter(
                    Q(from_building=from_building, to_building=to_buidling)
                    | Q(from_building=to_buidling, to_building=from_building)
                )
            ):
                from_device_uisp_dict = get_uisp_device_detail(
                    uisp_link["from"]["device"]["identification"]["id"], uisp_session
                )
                to_device_uisp_dict = get_uisp_device_detail(
                    uisp_link["to"]["device"]["identification"]["id"], uisp_session
                )

                last_seen_date = min(
                    datetime.datetime.fromisoformat(from_device_uisp_dict["overview"]["lastSeen"]),
                    datetime.datetime.fromisoformat(to_device_uisp_dict["overview"]["lastSeen"]),
                ).date()
                los = LOS(
                    from_building=from_building,
                    to_building=to_buidling,
                    source=LOS.LOSSource.EXISTING_LINK,
                    analysis_date=last_seen_date,
                    notes=f"Imported from UISP link",
                )
                los.save()

        if len(
            Link.objects.filter(
                Q(from_device=from_device, to_device=to_device) | Q(from_device=to_device, to_device=from_device)
            )
        ):
            logging.debug(f"Skipping duplicate link between {from_device} and {to_device}")
            continue

        if uisp_link["state"] == "active":
            status = Link.LinkStatus.ACTIVE
        else:
            status = Link.LinkStatus.INACTIVE

        link = Link(
            from_device=from_device,
            to_device=to_device,
            status=status,
            type=get_link_type(uisp_link),
            uisp_id=uisp_link["id"],
            # UISP doesn't track the following info, but we can maybe fill it in below from spreadsheet data
            install_date=None,
            abandon_date=None,
            description=None,
            notes=None,
        )
        link.save()

    for spreadsheet_link in spreadsheet_links:
        try:
            from_node = get_node_from_spreadsheet_id(spreadsheet_link.from_node_id)
            to_node = get_node_from_spreadsheet_id(spreadsheet_link.to_node_id)

            # If this link is between campus AP devices, try to avoid the get_representative_device_for_node
            # call, and instead look for the AP that we auto-created for the installs at each end of the link
            if "local ap" in spreadsheet_link.notes.lower():
                from_device = (
                    find_access_point_from_install_number(spreadsheet_link.from_node_id)
                    if not Node.objects.filter(network_number=spreadsheet_link.from_node_id)
                    else get_representative_device_for_node(from_node, spreadsheet_link.status)
                )
                to_device = (
                    find_access_point_from_install_number(spreadsheet_link.to_node_id)
                    if not Node.objects.filter(network_number=spreadsheet_link.to_node_id)
                    else get_representative_device_for_node(to_node, spreadsheet_link.status)
                )
                # If we found devices, make the link between them, otherwise fallback
                # to the default process below, so we don't drop the link
                if from_device and to_device:
                    link = create_link_for_device_pair(spreadsheet_link, from_device, to_device)
                    link.save()
                    continue

            for node in [from_node, to_node]:
                if not node:
                    raise ObjectDoesNotExist()
        except ObjectDoesNotExist:
            logging.warning(
                f"Skipping link {spreadsheet_link.from_node_id} to {spreadsheet_link.to_node_id}. "
                f"Can't find one or more nodes"
            )
            continue

        existing_links = Link.objects.filter(
            Q(from_device__node=from_node, to_device__node=to_node)
            | Q(to_device__node=from_node, from_device__node=to_node)
        )

        link_notes = "\n".join([spreadsheet_link.notes, spreadsheet_link.comments]).strip()

        if len(existing_links):
            if len(existing_links) > 1:
                logging.info(
                    f"Duplicate links detected between {from_node} and {to_node}, "
                    f"annotating all of them with the same spreadsheet metadata"
                )
            for link in existing_links:
                link.status = convert_spreadsheet_link_status(spreadsheet_link.status)
                link.install_date = spreadsheet_link.install_date
                if link.type in [Link.LinkType.FIVE_GHZ, Link.LinkType.ETHERNET]:
                    # If UISP indicates a special type of link, keep that.
                    # Otherwise, defer to the spreadsheet
                    link.type = (
                        convert_spreadsheet_link_type(spreadsheet_link.status, link_notes) or Link.LinkType.FIVE_GHZ
                    )
                link.abandon_date = spreadsheet_link.abandon_date
                link.description = spreadsheet_link.where_to_where if spreadsheet_link.where_to_where else None
                link.notes = link_notes if link_notes else None
                link.save()
        else:
            # If we don't have any possible existing links to annotate, make a brand new one
            if from_node.network_number and to_node.network_number:
                # If we don't have a network number for one of the sides, just rely on the LOS
                # we created above instead, so we don't end up with bogus "NNNone" placeholder devices
                link = create_link(spreadsheet_link, from_node, to_node)
                if link:
                    link.save()


if __name__ == "__main__":
    links_path = "spreadsheet_data/links.csv"
    load_links_supplement_with_uisp(get_spreadsheet_links((links_path)))

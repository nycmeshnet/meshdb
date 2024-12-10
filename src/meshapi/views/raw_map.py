import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from json.decoder import JSONDecodeError
from typing import Optional

from django.db import IntegrityError, transaction
from django.db.models import Q, Prefetch
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from ipware import get_client_ip
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_dataclasses.serializers import DataclassSerializer
from validate_email.exceptions import EmailValidationError

from meshapi.exceptions import AddressError
from meshapi.models import AddressTruthSource, Building, Install, Member, Node, install
from meshapi.permissions import HasNNAssignPermission, LegacyNNAssignmentPassword
from meshapi.serializers import MemberSerializer
from meshapi.serializers.map import EXCLUDED_INSTALL_STATUSES, MapDataInstallSerializer
from meshapi.util.admin_notifications import notify_administrators_of_data_issue
from meshapi.util.constants import RECAPTCHA_CHECKBOX_TOKEN_HEADER, RECAPTCHA_INVISIBLE_TOKEN_HEADER
from meshapi.util.django_pglocks import advisory_lock
from meshapi.util.network_number import NETWORK_NUMBER_MAX, NETWORK_NUMBER_MIN, get_next_available_network_number
from meshapi.validation import (
    NYCAddressInfo,
    geocode_nyc_address,
    normalize_phone_number,
    validate_email_address,
    validate_phone_number,
    validate_recaptcha_tokens,
)


@dataclass
class MapNode:
    id: int
    name: str
    status: str
    coordinates: list[float]
    requestDate: int
    installDate: int
    roofAccess: bool
    notes: str
    panoramas: list[str]


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def raw_map_data_node_list(request: Request) -> Response:
    all_installs = []
    queryset = (
        Install.objects.select_related("building")
        .select_related("node")
        .prefetch_related("node__installs")
        .prefetch_related("node__devices")
        .filter(~Q(status__in=EXCLUDED_INSTALL_STATUSES))
    )

    # Install -> dict
    for install in queryset:
        map_node = {
            "id": install.install_number,
            "name": install.member.name,
            "status": install.status,
            "coordinates": [install.building.latitude, install.building.longitude, install.building.altitude],
            "requestDate": int(install.request_date.timestamp() * 1000),
            "installDate": int(
                datetime.combine(install.install_date, datetime.min.time()).timestamp()
                * 1000
            )
            if install.install_date
            else None,
            "roofAccess": install.roof_access,
            "notes": MapDataInstallSerializer.get_synthetic_notes(install),
            "panoramas": install.building.panoramas,
        }

        for key in ["name", "status", "notes", "installDate"]:
            if map_node[key] is None:
                del map_node[key]

        all_installs.append(map_node)

    # We need to make sure there is an entry on the map for every NN, and since we excluded the
    # NN assigned rows in the query above, we need to go through the Node objects and
    # include the nns we haven't already covered via install num
    covered_nns = {install["id"] for install in all_installs}
    for node in (
        Node.objects.filter(~Q(status=Node.NodeStatus.INACTIVE))
        .prefetch_related("devices")
        .prefetch_related("installs")
        .prefetch_related("buildings")
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
        if node.network_number and node.network_number not in covered_nns:
            # Arbitrarily pick a representative install for the details of the "Fake" node,
            # preferring active installs if possible
            try:
                representative_install = (
                    node.active_installs  # type: ignore[attr-defined]
                    or node.prefetched_installs  # type: ignore[attr-defined]
                )[0]
            except IndexError:
                representative_install = None

            if representative_install:
                building = representative_install.building
            else:
                building = node.buildings.first()

            # if not building:
            #    # If we couldn't get a building from the install or node,
            #    # make a faux one instead, to carry the lat/lon info into the serializer
            #    building = Building(
            #        latitude=node.latitude,
            #        longitude=node.longitude,
            #        altitude=node.altitude,
            #    )

            # all_installs.append(
            #    Install(
            #        install_number=node.network_number,
            #        node=node,
            #        status=Install.InstallStatus.NN_REASSIGNED
            #        if node.status == node.NodeStatus.ACTIVE
            #        else Install.InstallStatus.REQUEST_RECEIVED,
            #        building=building,
            #        request_date=representative_install.request_date if representative_install else node.install_date,
            #        roof_access=representative_install.roof_access if representative_install else True,
            #    ),
            # )

            if representative_install and representative_install.install_date:
                installDate = int(
                    datetime.combine(representative_install.install_date, datetime.min.time()).timestamp()
                    * 1000
                )
            elif node.install_date:
                installDate = int(
                    datetime.combine(node.install_date, datetime.min.time()).timestamp()
                    * 1000
                )
            else:
                installDate = None


            # Install -> dict
            map_node = {
                "id": node.network_number,
                "name": representative_install.member.name,
                "status": Install.InstallStatus.NN_REASSIGNED,
                "coordinates": [
                    building.latitude if building else node.latitude,
                    building.longitude if building else node.longitude,
                    building.altitude if building else node.altitude,
                ],
                "requestDate": int(representative_install.request_date.timestamp() * 1000),
                "installDate": installDate,
                "roofAccess": representative_install.roof_access if representative_install else True,
                "notes": MapDataInstallSerializer.get_synthetic_notes(representative_install),
                "panoramas": node.buildings.first().panoramas if node.buildings else [],
            }

            for key in ["name", "status", "notes", "installDate"]:
                if map_node[key] is None:
                    del map_node[key]

            all_installs.append(map_node)

            covered_nns.add(node.network_number)

    all_installs.sort(key=lambda i: i["id"])

    return Response(
        all_installs, status=status.HTTP_200_OK
    )

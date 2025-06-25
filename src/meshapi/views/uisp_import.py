import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from meshapi.tasks import run_uisp_on_demand_import
from meshapi.util.network_number import NETWORK_NUMBER_MAX, NETWORK_NUMBER_MIN
from meshdb.celery import app


@extend_schema_view(
    summary="View status for UISP Import jobs.",
    post=extend_schema(tags=["UISP Import"]),
    responses={
        "200": OpenApiResponse(
            description="API is up and serving traffic",
            response=OpenApiTypes.STR,
        ),
        "500": OpenApiResponse(
            description="Server error, probbaly a misconfigured environment variable.",
            response=OpenApiTypes.STR,
        ),
    },
)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def view_uisp_on_demand_import_status(request: Request) -> Response:
    try:
        # Inspect all nodes.
        i = app.control.inspect()

        # Show the items that have an ETA or are scheduled for later processing
        scheduled = i.scheduled()

        # Show tasks that are currently active.
        active = i.active()

        # Show tasks that have been claimed by workers
        reserved = i.reserved()

        tasks = []

        def parse_tasks(tasks_by_worker: dict[str, list], status: str) -> list[dict[str, str]]:
            parsed_tasks = []
            for _, tasks in tasks_by_worker.items():
                for t in tasks:
                    if "run_uisp_on_demand_import" in t.get("name"):
                        parsed_tasks.append({"id": t.get("id"), "nn": t.get("args")[0], "status": status})
            return parsed_tasks

        tasks.extend(parse_tasks(active, "running"))
        tasks.extend(parse_tasks(reserved, "claimed"))
        tasks.extend(parse_tasks(scheduled, "scheduled"))

    except Exception as e:
        logging.exception(e)
        return Response({"detail": "An error occurred trying to fetch task status"}, status=500)

    return Response({"tasks": tasks}, status=200)


@extend_schema_view(
    summary="Run the UISP Import job for a single Network Number.",
    post=extend_schema(tags=["UISP Import"]),
    responses={
        "200": OpenApiResponse(
            description="API is up and serving traffic",
            response=OpenApiTypes.STR,
        ),
        "400": OpenApiResponse(
            description="User provided invalid input in slug",
            response=OpenApiTypes.STR,
        ),
        "500": OpenApiResponse(
            description="Server error, probbaly a misconfigured environment variable.",
            response=OpenApiTypes.STR,
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAdminUser])
def uisp_import_for_nn(request: Request, network_number: int) -> Response:
    logging.info(f"Received uisp import request for NN{network_number}")
    if not network_number:
        status = 404
        m = "Please provide a network number."
        logging.error(m)
        return Response({"detail": m}, status=status)

    try:
        target_nn = int(network_number)  # Because I apparently can't trust nobody
        # Must be in valid range.
        # NETWORK_NUMBER_MIN is set to something meshdb can assign new stuff, but we have lower NNs
        # hence, I hardcode 1
        FIRST_NN = 1
        if target_nn < FIRST_NN or NETWORK_NUMBER_MAX < target_nn:
            status = 404
            m = f"Network Number must be an integer between {NETWORK_NUMBER_MIN} and {NETWORK_NUMBER_MAX}."
            logging.error(m)
            return Response({"detail": m}, status=status)
    except ValueError:
        # Sanity check. This should never happen.
        status = 400
        m = f"Network Number must be an integer between {NETWORK_NUMBER_MIN} and {NETWORK_NUMBER_MAX}."
        return Response({"detail": m}, status=status)

    try:
        import_result = run_uisp_on_demand_import.delay(target_nn)
    except Exception as e:
        logging.exception(e)
        return Response({"detail": "error", "task_id": None}, status=500)

    logging.info(
        f"UISP Import for NN{network_number} is now running with Task ID {import_result.id}."
        " Check the object in a few minutes to see updates."
    )
    return Response({"detail": "success", "task_id": import_result.id}, status=200)

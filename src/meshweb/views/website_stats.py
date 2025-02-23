import io
import math
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, cast

import matplotlib.pyplot as plt
import numpy as np
from corsheaders.signals import check_request_enabled
from django.db.models import Min
from django.dispatch import receiver
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from matplotlib import ticker

from meshapi.models import Install

# Make the SVG output include text instead of strokes
plt.rcParams["svg.fonttype"] = "none"

VALID_DATA_MODES = ["install_requests", "active_installs"]
GRAPH_X_AXIS_DATAPOINT_COUNT = 100

# Matplotlib is not thread safe, so when the browser makes concurrent requests, we might accidentally
# mix the configuration of multiple requests. This mutex protects all access to matplotlib functions
matplotlib_lock = threading.Lock()


@receiver(check_request_enabled)
def cors_allow_website_stats_to_all(sender: None, request: HttpRequest, **kwargs: dict) -> bool:
    """
    This handler adds an allow all CORS header to the stats endpoints for nycmesh.net and the
    netlify-hosted test domains created during PRs
    """
    if request.path not in [
        reverse("legacy-stats-svg"),
        reverse("legacy-stats-json"),
    ]:
        return False

    origin: Optional[str] = cast(Optional[str], request.META.get("HTTP_ORIGIN"))
    if not origin:
        return False

    if re.fullmatch(r"https://deploy-preview-\d{1,5}--nycmesh-website\.netlify\.app", origin):
        return True

    if origin in ["https://nycmesh.net", "https://www.nycmesh.net"]:
        return True

    return False


def compute_graph_stats(data_source: str, start_datetime: datetime, end_datetime: datetime) -> List[int]:
    buckets = [0 for _ in range(GRAPH_X_AXIS_DATAPOINT_COUNT)]

    total_duration_seconds = (end_datetime - start_datetime).total_seconds()
    base_object_queryset = Install.objects.all()

    if data_source == "active_installs":
        # FYI This logic doesn't account for installs that have been abandoned,
        # so it definitely underestimates historical values
        base_object_queryset = base_object_queryset.filter(status=Install.InstallStatus.ACTIVE)
        object_queryset = base_object_queryset.filter(
            install_date__gte=start_datetime.date(),
            install_date__lte=end_datetime.date(),
        )
        buckets[0] = base_object_queryset.filter(install_date__lt=start_datetime).count()
    else:
        object_queryset = base_object_queryset.filter(
            request_date__gte=start_datetime.date(),
            request_date__lte=end_datetime.date(),
        )
        buckets[0] = base_object_queryset.filter(request_date__lt=start_datetime).count()

    for install in object_queryset:
        if data_source == "active_installs":
            counting_date = install.install_date or install.request_date.date()
        else:
            counting_date = install.request_date.date()

        relative_seconds = (counting_date - start_datetime.date()).total_seconds()
        bucket_index = math.floor((relative_seconds / total_duration_seconds) * GRAPH_X_AXIS_DATAPOINT_COUNT)
        buckets[bucket_index] += 1

    # Make cumulative
    for i in range(GRAPH_X_AXIS_DATAPOINT_COUNT):
        if i > 0:
            buckets[i] += buckets[i - 1]

    return buckets


def render_graph(
    data_source: str,
    data_buckets: List[int],
    start_datetime: datetime,
    end_datetime: datetime,
) -> str:
    plt.figure()
    x = np.arange(0, GRAPH_X_AXIS_DATAPOINT_COUNT, 1)
    y = data_buckets

    fig, ax = plt.subplots(figsize=(6, 3.75))

    plot_color = "#ff3a30" if data_source == "active_installs" else "#aaaaaa"
    ax.plot(y, color=plot_color)
    ax.fill_between(x, y, 0, alpha=0.125, color=plot_color)

    total_duration = end_datetime - start_datetime
    if total_duration < timedelta(days=366):
        if total_duration < timedelta(days=8):
            vertical_divisions = 7
        elif total_duration < timedelta(days=32):
            vertical_divisions = 4
        else:
            vertical_divisions = 12

        ax.minorticks_on()
        ax.xaxis.set_minor_locator(ticker.MultipleLocator((GRAPH_X_AXIS_DATAPOINT_COUNT - 1) / vertical_divisions))

    plt.grid(which="minor", axis="x", color="#eeeeee", linewidth=1)

    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.set_yticks([data_buckets[0], data_buckets[-1]])
    ax.tick_params(axis="both", which="both", length=0)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.set_ylim((data_buckets[0], data_buckets[-1]))
    ax.yaxis.tick_right()
    ax.tick_params(
        axis="both",
        which="both",
        labelcolor="#777",
        length=0,
        labelsize=12,
        pad=-8,
        labelfontfamily="Helvetica Neue",
    )
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    ax2 = ax.secondary_xaxis("bottom")
    ax2.set_xticklabels(
        [
            start_datetime.date().strftime("%b %-d, %Y"),
            end_datetime.date().strftime("%b %-d, %Y"),
        ],
        position=(-1, -GRAPH_X_AXIS_DATAPOINT_COUNT),
    )
    ax2.set_ticks([int(GRAPH_X_AXIS_DATAPOINT_COUNT * 0.09), int(GRAPH_X_AXIS_DATAPOINT_COUNT * 0.89)])
    ax2.tick_params(
        axis="both",
        which="both",
        labelcolor="#777",
        length=0,
        labelsize=12,
        pad=10,
        labelfontfamily="Helvetica Neue",
    )

    ax2.spines["top"].set_visible(False)
    ax2.spines["bottom"].set_visible(False)

    plt.tight_layout()

    buf = io.StringIO()
    plt.savefig(buf, format="svg")

    return buf.getvalue()


def parse_stats_request_params(request: HttpRequest) -> Tuple[str, datetime, datetime]:
    days = int(request.GET.get("days", 0))
    if days < 0:
        raise ValueError("Invalid number of days to aggregate data for")

    data_source = request.GET.get("data", "install_requests")
    if data_source not in VALID_DATA_MODES:
        raise ValueError(f"Invalid data mode param, expecting one of: {VALID_DATA_MODES}")

    if days > 0:
        start_datetime = datetime.now(timezone.utc) - timedelta(days=days)
    else:
        # "All" Case
        initial_date = Install.objects.all().aggregate(Min("request_date"))["request_date__min"]
        if initial_date is None:
            raise EnvironmentError("No installs found, is the database empty?")

        start_datetime = datetime.combine(
            Install.objects.all().aggregate(Min("request_date"))["request_date__min"].date(),
            datetime.min.time(),
        ).astimezone(timezone.utc)
    end_datetime = datetime.now(timezone.utc)

    return data_source, start_datetime, end_datetime


def website_stats_graph(request: HttpRequest) -> HttpResponse:
    """
    Renders an SVG graph for embedding on the website, showing install growth over time

    Accepts two optional HTTP GET Params:
     days - an integer representing the number of days prior to the current date to render graphs for (default: "all")
     data - the data mode to use, either "install_requests" or "active_installs" (default: "install_requests")

    Returns HTTP 400 with a plain text description of the error if anything is wrong with these
    params, otherwise HTTP 200 with the response content being an SVG XML which is ready for browser
    embedding and display
    """
    try:
        data_source, start_datetime, end_datetime = parse_stats_request_params(request)
    except ValueError as e:
        return HttpResponse(status=400, content=e.args[0])
    except EnvironmentError as e:
        return HttpResponse(status=500, content=e.args[0])

    datapoints = compute_graph_stats(data_source, start_datetime, end_datetime)

    with matplotlib_lock:
        return HttpResponse(
            render_graph(data_source, datapoints, start_datetime, end_datetime), content_type="image/svg+xml"
        )


def website_stats_json(request: HttpRequest) -> HttpResponse:
    """
    Renders an JSON response containing the information in the stats graphs rendered above,
    showing install growth over time

    Accepts two optional HTTP GET Params:
     days - an integer representing the number of days prior to the current date to pull stats for (default: "all")
     data - the data mode to use, either "install_requests" or "active_installs" (default: "install_requests")

    Returns HTTP 400 with a plain text description of the error if anything is wrong with these
    params, otherwise HTTP 200 with the response content being an JSON data containing map render info
    """
    try:
        data_source, start_datetime, end_datetime = parse_stats_request_params(request)
    except ValueError as e:
        return JsonResponse(status=400, data={"error": e.args[0]})
    except EnvironmentError as e:
        return JsonResponse(status=500, data={"error": e.args[0]})

    datapoints = compute_graph_stats(data_source, start_datetime, end_datetime)
    return JsonResponse(
        {
            "start": int(start_datetime.timestamp()),
            "end": int(end_datetime.timestamp()),
            "data": datapoints,
        }
    )

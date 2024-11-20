import datetime
import io
import math

import matplotlib.pyplot as plt
import numpy as np
from django.db.models import Min
from django.http import HttpRequest, HttpResponse
from matplotlib import ticker

from meshapi.models import Install

# Make the SVG output include text instead of strokes
plt.rcParams["svg.fonttype"] = "none"

VALID_DATA_MODES = ["install_requests", "active_installs"]


def compute_graph_stats():
    pass


def render_graph():
    pass


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
        days = int(request.GET.get("days", 0))
        if days < 0:
            raise ValueError()
    except ValueError:
        return HttpResponse(status=400, content="Invalid number of days to aggregate data for")

    data_source = request.GET.get("data", "install_requests")
    if data_source not in VALID_DATA_MODES:
        return HttpResponse(status=400, content=f"Invalid data mode param, expecting one of: {VALID_DATA_MODES}")

    if Install.objects.count() == 0:
        return HttpResponse(
            status=500,
            content='<svg xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://www.w3.org/2000/svg" '
            + 'width="432pt" height="270pt" '
            + 'viewBox="-10 -20 500 20" '
            + 'version="1.1">'
            + "<text>No installs found, is the database empty?</text>"
            + "</svg>",
            content_type="image/svg+xml",
        )

    intervals = 100
    buckets = [0 for _ in range(intervals)]

    if days > 0:
        start_time = datetime.datetime.now() - datetime.timedelta(days=days)
    else:
        # "All" Case
        start_time = datetime.datetime.combine(
            Install.objects.all().aggregate(Min("request_date"))["request_date__min"],
            datetime.datetime.min.time(),
        )
    end_time = datetime.datetime.now()
    total_duration = end_time - start_time
    total_duration_seconds = total_duration.total_seconds()

    base_object_queryset = Install.objects.all()

    if data_source == "active_installs":
        # FYI This logic doesn't account for installs that have been abandoned,
        # so it definitely underestimates historical values
        base_object_queryset = base_object_queryset.filter(status=Install.InstallStatus.ACTIVE)
        object_queryset = base_object_queryset.filter(
            install_date__gte=start_time.date(),
            install_date__lte=end_time.date(),
        )
        buckets[0] = base_object_queryset.filter(install_date__lt=start_time).count()
    else:
        object_queryset = base_object_queryset.filter(
            request_date__gte=start_time.date(),
            request_date__lte=end_time.date(),
        )
        buckets[0] = base_object_queryset.filter(request_date__lt=start_time).count()

    for install in object_queryset:
        if data_source == "active_installs":
            counting_date = install.install_date or install.request_date
        else:
            counting_date = install.request_date

        relative_seconds = (counting_date - start_time.date()).total_seconds()
        bucket_index = math.floor((relative_seconds / total_duration_seconds) * intervals)
        buckets[bucket_index] += 1

    # Make cumulative
    for i in range(intervals):
        if i > 0:
            buckets[i] += buckets[i - 1]

    plt.figure()
    x = np.arange(0, intervals, 1)
    y = buckets

    fig, ax = plt.subplots(figsize=(6, 3.75))

    plot_color = "#ff3a30" if data_source == "active_installs" else "#aaaaaa"
    ax.plot(y, color=plot_color)
    ax.fill_between(x, y, 0, alpha=0.125, color=plot_color)

    if total_duration < datetime.timedelta(days=366):
        if total_duration < datetime.timedelta(days=8):
            vertical_divisions = 7
        elif total_duration < datetime.timedelta(days=32):
            vertical_divisions = 4
        else:
            vertical_divisions = 12

        ax.minorticks_on()
        ax.xaxis.set_minor_locator(ticker.MultipleLocator((intervals - 1) / vertical_divisions))

    plt.grid(which="minor", axis="x", color="#eeeeee", linewidth=1)

    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.set_yticks([buckets[0], buckets[-1]])
    ax.tick_params(axis="both", which="both", length=0)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.set_ylim((buckets[0], buckets[-1]))
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
            start_time.date().strftime("%b %-d, %Y"),
            end_time.date().strftime("%b %-d, %Y"),
        ],
        position=(-1, -100),
    )
    ax2.set_ticks([8, intervals - 8])
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

    buf = io.BytesIO()
    plt.savefig(buf, format="svg")

    return HttpResponse(buf.getvalue(), content_type="image/svg+xml")

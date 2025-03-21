from django.urls import include, path

from meshweb import views

urlpatterns = [
    path("", views.index, name="main"),
    path("maintenance/", views.maintenance, name="maintenance"),
    path("maintenance/enable/", views.enable_maintenance, name="maintenance-enable"),
    path("maintenance/disable/", views.disable_maintenance, name="maintenance-disable"),
    path("website-embeds/stats-graph.svg", views.website_stats_graph, name="legacy-stats-svg"),
    path("website-embeds/stats-graph.json", views.website_stats_json, name="legacy-stats-json"),
    path("explorer/", include("explorer.urls")),
    path("join-records/view/", views.join_record_viewer, name="join-record-viewer"),
    path("uisp-on-demand/", views.uisp_on_demand_form, name="uisp-on-demand"),
]

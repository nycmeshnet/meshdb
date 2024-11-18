from django.urls import include, path

from meshweb import views

urlpatterns = [
    path("", views.index, name="main"),
    path("maintenance/", views.maintenance, name="maintenance"),
    path("maintenance/enable/", views.enable_maintenance, name="maintenance-enable"),
    path("maintenance/disable/", views.disable_maintenance, name="maintenance-disable"),
    path("website-embeds/stats-graph.svg", views.website_stats_graph, name="legacy-stats"),
    path("explorer/", include("explorer.urls")),
]

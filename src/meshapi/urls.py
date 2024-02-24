from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns

from meshapi import views

urlpatterns = [
    path("", views.api_root),
    path("buildings/", views.BuildingList.as_view(), name="meshapi-v1-building-list"),
    path("buildings/<int:pk>/", views.BuildingDetail.as_view(), name="meshapi-v1-building-detail"),
    path("members/", views.MemberList.as_view(), name="meshapi-v1-member-list"),
    path("members/<int:pk>/", views.MemberDetail.as_view(), name="meshapi-v1-member-detail"),
    path("installs/", views.InstallList.as_view(), name="meshapi-v1-install-list"),
    path("installs/<int:pk>/", views.InstallDetail.as_view(), name="meshapi-v1-install-detail"),
    path("nodes/", views.NodeList.as_view(), name="meshapi-v1-node-list"),
    path("nodes/<int:pk>/", views.NodeDetail.as_view(), name="meshapi-v1-node-detail"),
    path("links/", views.LinkList.as_view(), name="meshapi-v1-link-list"),
    path("links/<int:pk>/", views.LinkDetail.as_view(), name="meshapi-v1-link-detail"),
    path("sectors/", views.SectorList.as_view(), name="meshapi-v1-sector-list"),
    path("sectors/<int:pk>/", views.SectorDetail.as_view(), name="meshapi-v1-sector-detail"),
    path("devices/", views.DeviceList.as_view(), name="meshapi-v1-device-list"),
    path("devices/<int:pk>/", views.DeviceDetail.as_view(), name="meshapi-v1-device-detail"),
    path("join/", views.join_form, name="meshapi-v1-join"),
    path("nn-assign/", views.network_number_assignment, name="meshapi-v1-nn-assign"),
    path("buildings/lookup/", views.LookupBuilding.as_view(), name="meshapi-v1-lookup-building"),
    path("members/lookup/", views.LookupMember.as_view(), name="meshapi-v1-lookup-member"),
    path("installs/lookup/", views.LookupInstall.as_view(), name="meshapi-v1-lookup-install"),
    path("nodes/lookup/", views.LookupNode.as_view(), name="meshapi-v1-lookup-node"),
    path("devices/lookup/", views.LookupDevice.as_view(), name="meshapi-v1-lookup-device"),
    path("links/lookup/", views.LookupLink.as_view(), name="meshapi-v1-lookup-link"),
    path("sectors/lookup/", views.LookupSector.as_view(), name="meshapi-v1-lookup-sector"),
    path("query/buildings/", views.QueryBuilding.as_view(), name="meshapi-v1-query-building"),
    path("query/members/", views.QueryMember.as_view(), name="meshapi-v1-query-member"),
    path("query/installs/", views.QueryInstall.as_view(), name="meshapi-v1-query-install"),
    path("mapdata/nodes/", views.MapDataNodeList.as_view(), name="meshapi-v1-map-data-installs"),
    path("mapdata/links/", views.MapDataLinkList.as_view(), name="meshapi-v1-map-data-links"),
    path("mapdata/sectors/", views.MapDataSectorList.as_view(), name="meshapi-v1-map-data-sectors"),
    path("geography/whole-mesh.kml", views.WholeMeshKML.as_view(), name="meshapi-v1-geography-whole-mesh-kml"),
    path("update-panos/", views.update_panos, name="meshapi-v1-update-panos")
]

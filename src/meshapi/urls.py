from django.urls import path

from meshapi import views

urlpatterns = [
    path("", views.api_root),
    path("buildings/", views.BuildingList.as_view(), name="meshapi-v1-building-list"),
    path("buildings/<uuid:pk>/", views.BuildingDetail.as_view(), name="meshapi-v1-building-detail"),
    path("members/", views.MemberList.as_view(), name="meshapi-v1-member-list"),
    path("members/<uuid:pk>/", views.MemberDetail.as_view(), name="meshapi-v1-member-detail"),
    path("installs/", views.InstallList.as_view(), name="meshapi-v1-install-list"),
    path("installs/<uuid:pk>/", views.InstallDetail.as_view(), name="meshapi-v1-install-detail"),
    path(
        "installs/<int:install_number>/",
        views.InstallDetailByInstallNumber.as_view(),
        name="meshapi-v1-install-detail-by-number",
    ),
    path("nodes/", views.NodeList.as_view(), name="meshapi-v1-node-list"),
    path("nodes/<uuid:pk>/", views.NodeDetail.as_view(), name="meshapi-v1-node-detail"),
    path(
        "nodes/<int:network_number>/",
        views.NodeDetailByNetworkNumber.as_view(),
        name="meshapi-v1-node-detail-by-number",
    ),
    path("links/", views.LinkList.as_view(), name="meshapi-v1-link-list"),
    path("links/<uuid:pk>/", views.LinkDetail.as_view(), name="meshapi-v1-link-detail"),
    path("loses/", views.LOSList.as_view(), name="meshapi-v1-los-list"),
    path("loses/<uuid:pk>/", views.LOSDetail.as_view(), name="meshapi-v1-los-detail"),
    path("sectors/", views.SectorList.as_view(), name="meshapi-v1-sector-list"),
    path("sectors/<uuid:pk>/", views.SectorDetail.as_view(), name="meshapi-v1-sector-detail"),
    path("accesspoints/", views.AccessPointList.as_view(), name="meshapi-v1-accesspoint-list"),
    path("accesspoints/<uuid:pk>/", views.AccessPointDetail.as_view(), name="meshapi-v1-accesspoint-detail"),
    path("devices/", views.DeviceList.as_view(), name="meshapi-v1-device-list"),
    path("devices/<uuid:pk>/", views.DeviceDetail.as_view(), name="meshapi-v1-device-detail"),
    path("join/", views.join_form, name="meshapi-v1-join"),
    path("nn-assign/", views.network_number_assignment, name="meshapi-v1-nn-assign"),
    path(
        "disambiguate-number/",
        views.DisambiguateInstallOrNetworkNumber.as_view(),
        name="meshapi-v1-disambiguate-number",
    ),
    path("crawl-uisp-for-nn/", views.crawl_usip_for_nn, name="crawl-uisp-for-nn"),
    path("buildings/lookup/", views.LookupBuilding.as_view(), name="meshapi-v1-lookup-building"),
    path("members/lookup/", views.LookupMember.as_view(), name="meshapi-v1-lookup-member"),
    path("installs/lookup/", views.LookupInstall.as_view(), name="meshapi-v1-lookup-install"),
    path("nodes/lookup/", views.LookupNode.as_view(), name="meshapi-v1-lookup-node"),
    path("devices/lookup/", views.LookupDevice.as_view(), name="meshapi-v1-lookup-device"),
    path("links/lookup/", views.LookupLink.as_view(), name="meshapi-v1-lookup-link"),
    path("loses/lookup/", views.LookupLOS.as_view(), name="meshapi-v1-lookup-los"),
    path("sectors/lookup/", views.LookupSector.as_view(), name="meshapi-v1-lookup-sector"),
    path("accesspoints/lookup/", views.LookupAccessPoint.as_view(), name="meshapi-v1-lookup-accesspoint"),
    path("query/buildings/", views.QueryBuilding.as_view(), name="meshapi-v1-query-building"),
    path("query/members/", views.QueryMember.as_view(), name="meshapi-v1-query-member"),
    path("query/installs/", views.QueryInstall.as_view(), name="meshapi-v1-query-install"),
    path("mapdata/nodes/", views.MapDataNodeList.as_view(), name="meshapi-v1-map-data-installs"),
    path("mapdata/links/", views.MapDataLinkList.as_view(), name="meshapi-v1-map-data-links"),
    path("mapdata/sectors/", views.MapDataSectorList.as_view(), name="meshapi-v1-map-data-sectors"),
    path("mapdata/kiosks/", views.KioskListWrapper.as_view(), name="meshapi-v1-map-data-kiosks"),
    path("geography/whole-mesh.kml", views.WholeMeshKML.as_view(), name="meshapi-v1-geography-whole-mesh-kml"),
    path("geography/nyc-geocode/v2/search", views.NYCGeocodeWrapper.as_view(), name="meshapi-v1-geography-geocode"),
]

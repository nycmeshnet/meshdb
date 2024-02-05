from django.db.models import Q
from rest_framework import generics, permissions

from meshapi.models import Building, Install, Link, Sector
from meshapi.serializers import MapDataInstallSerializer, MapDataLinkSerializer, MapDataSectorSerializer


class MapDataInstallList(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MapDataInstallSerializer
    pagination_class = None

    def get_queryset(self):
        all_installs = []

        queryset = Install.objects.filter(~Q(install_status__in=[Install.InstallStatus.CLOSED]))

        for install in queryset:
            all_installs.append(install)

        for building in Building.objects.filter(primary_nn__isnull=False):
            representative_install = building.installs.all()[0]
            all_installs.append(
                Install(
                    install_number=building.primary_nn,
                    install_status=Install.InstallStatus.NN_ASSIGNED,
                    building=building,
                    request_date=representative_install.request_date,
                    roof_access=representative_install.roof_access,
                ),
            )

        all_installs.sort(key=lambda i: i.install_number)
        return all_installs


class MapDataLinkList(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MapDataLinkSerializer
    pagination_class = None
    queryset = Link.objects.filter(~Q(status__in=[Link.LinkStatus.DEAD]))


class MapDataSectorlList(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MapDataSectorSerializer
    pagination_class = None
    queryset = Sector.objects.all()

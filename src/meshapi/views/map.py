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

        excluded_statuses = {
            Install.InstallStatus.CLOSED,
            Install.InstallStatus.NN_REASSIGNED,
        }

        queryset = Install.objects.filter(~Q(install_status__in=excluded_statuses))

        for install in queryset:
            all_installs.append(install)

        # We need to make sure there is an entry on the map for every NN, and since we excluded the
        # NN assigned rows in the query above, we need to go through the building objects and
        # include the nns we haven't already covered via install num
        covered_nns = {
            install.network_number for install in all_installs if install.install_number == install.network_number
        }
        for building in Building.objects.filter(
            Q(
                primary_nn__isnull=False,
                building_status=Building.BuildingStatus.ACTIVE,
            )
            & Q(installs__install_status__in=set(Install.InstallStatus.values) - excluded_statuses)
        ):
            if building.primary_nn not in covered_nns:
                representative_install = building.installs.all()[0]
                all_installs.append(
                    Install(
                        install_number=building.primary_nn,
                        install_status=Install.InstallStatus.NN_REASSIGNED,
                        building=building,
                        request_date=representative_install.request_date,
                        roof_access=representative_install.roof_access,
                    ),
                )
                covered_nns.add(building.primary_nn)

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
    queryset = Sector.objects.filter(~Q(status__in=[Sector.SectorStatus.ABANDONED]))

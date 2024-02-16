from meshapi import models


def get_building_from_node_id(node_id: int) -> models.Building:
    install_obj = models.Install.objects.filter(install_number=node_id).first()
    if install_obj and install_obj.InstallStatus != models.Install.InstallStatus.NN_REASSIGNED:
        return install_obj.building

    install_obj = models.Install.objects.filter(network_number=node_id).first()
    if install_obj:
        return install_obj.building

    building_obj = models.Building.objects.filter(primary_nn=node_id).first()
    if building_obj:
        return building_obj

    raise ValueError(f"Could not find building for install #{node_id}")

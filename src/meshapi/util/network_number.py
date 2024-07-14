from django.apps import apps

NETWORK_NUMBER_MIN = 101
NETWORK_NUMBER_MAX = 8192


def get_next_available_network_number() -> int:
    """
    This function finds, and marks as re-assigned, the next install whose number can be re-assigned
    for use as a network number. This is non-trivial becuause we need to exclude installs that
    have non "REQUEST RECIEVED" statuses, as well as the set of all NNs that have been assigned
    to any other installs for any reason
    :return: the integer for the next available network number
    """

    # Since the contents of this file are used in the models.* files, imports get very circular very quick,
    # so we use Django's lazy-loading feature to get references to the model types without imports
    Install = apps.get_model("meshapi.Install")
    Node = apps.get_model("meshapi.Node")

    defined_nns = set(
        Install.objects.exclude(status=Install.InstallStatus.REQUEST_RECEIVED, node__isnull=True).values_list(
            "install_number", flat=True
        )
    ).union(set(Node.objects.values_list("network_number", flat=True)))

    # Find the first valid NN that isn't in use
    free_nn = next(i for i in range(NETWORK_NUMBER_MIN, NETWORK_NUMBER_MAX + 1) if i not in defined_nns)

    # Sanity check to make sure we don't assign something crazy. This is done by the query above,
    # but we want to be super sure we don't violate these constraints so we check it here
    if free_nn < NETWORK_NUMBER_MIN or free_nn > NETWORK_NUMBER_MAX:
        raise ValueError(f"Invalid NN: {free_nn}")

    # The number we are about to assign should not be connected to any existing installs as
    # an NN. Again, the above logic should do this, but we REALLY care about this not happening
    already_in_use_nn_qs = Install.objects.filter(node__network_number=free_nn)
    if len(already_in_use_nn_qs):
        raise ValueError(
            f"Invalid NN: {free_nn} is already in use for "
            f"install number {already_in_use_nn_qs.first().install_number}"
        )

    already_exists_node_qs = Node.objects.filter(network_number=free_nn)
    if len(already_exists_node_qs):
        raise ValueError(f"Invalid NN: {free_nn} is already the network_number for a pre-exisiting node")

    # If we are re-assigning a number from another install, mark it with NN Assigned to indicate
    # that this has happened
    nn_donor_install = Install.objects.select_for_update().filter(install_number=free_nn).first()
    if nn_donor_install:
        # Double check that if we are re-assigning something that has been used before that it is
        # definitely unused. The logic above should do that, but this is so important that for
        # safety that we should double-check
        if nn_donor_install.status != Install.InstallStatus.REQUEST_RECEIVED or nn_donor_install.node is not None:
            raise ValueError(
                f"Invalid NN: {free_nn} has an install associated that "
                f"looks active (#{nn_donor_install.install_number})"
            )

        nn_donor_install.status = Install.InstallStatus.NN_REASSIGNED
        nn_donor_install.save()

    return free_nn

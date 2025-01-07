import uuid
from typing import Optional

from django.apps import apps

NETWORK_NUMBER_MIN = 1
NETWORK_NUMBER_ASSIGN_MIN = 101
NETWORK_NUMBER_MAX = 8000


def no_op() -> None:
    """Literally does nothing, exists to provide a hook to the testing
    harness for race condition analysis"""
    pass


def validate_network_number_unused_and_claim_install_if_needed(
    network_number_candidate: int, pre_existing_node_id: Optional[uuid.UUID]
) -> None:
    """
    Helper function to encapsulate the validation logic for the attachment of an NN
    to a new node. We need to validate that the NN is unused as either an install number
    or network number on an existing node. However, there are some edge cases. For example,
    we allow an active install to have its number used as an NN for a node, if that node is
    attached to this install

    This validation logic is used for auto-assignment in the get_next_available_network_number()
    function below, but also on many Node.save() calls since vanity NNs can come in via the
    admin form and need to be validated prior to being committed to the DB

    Accepts an optional existing node id to exempt from validation, this allows
    assigning old install numbers to new nodes, even if the old installs are active,
    as long as you associate the node that is going to get the install number to that install before
    you try to assign the number to that node

    :param network_number_candidate: The candidate network number we would like to validate
    :param pre_existing_node_id: An optional existing node id to exempt from validation
    :return: None
    :raises ValueError if the network_number_candidate is invalid for any reason
    """
    # inline imports prevent cycles
    from meshapi.models import Install, Node

    if network_number_candidate < NETWORK_NUMBER_MIN or network_number_candidate > NETWORK_NUMBER_MAX:
        raise ValueError(f"Network number is invalid, must be between {NETWORK_NUMBER_MIN} and {NETWORK_NUMBER_MAX}")

    pre_existing_node_with_nn = Node.objects.filter(network_number=network_number_candidate).first()
    if pre_existing_node_with_nn is not None and pre_existing_node_with_nn.id != pre_existing_node_id:
        raise ValueError("Network number already in use by another node")

    nn_donor_install = Install.objects.select_for_update().filter(install_number=network_number_candidate).first()
    if nn_donor_install:
        if pre_existing_node_id and nn_donor_install.node_id == pre_existing_node_id:
            # If the install is already connected to the node that is going to receive the network number,
            # then the node can have that number without any further state updates or validation needed
            return

        if nn_donor_install.status == Install.InstallStatus.ACTIVE:
            raise ValueError(
                f"Invalid NN: {network_number_candidate} has an install associated that "
                f"looks active (#{nn_donor_install.install_number})"
            )

        if nn_donor_install.status != Install.InstallStatus.NN_REASSIGNED:
            nn_donor_install.status = Install.InstallStatus.NN_REASSIGNED
            nn_donor_install.save()


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
    free_nn = next(i for i in range(NETWORK_NUMBER_ASSIGN_MIN, NETWORK_NUMBER_MAX + 1) if i not in defined_nns)

    # At testing time this turns into a time.sleep() call to help expose race conditions
    no_op()

    # Sanity check to make sure we don't assign something crazy. This is done by the query above,
    # but we want to be super sure we don't violate these constraints so we check it here
    if free_nn < NETWORK_NUMBER_ASSIGN_MIN or free_nn > NETWORK_NUMBER_MAX:
        raise ValueError(f"Invalid NN: {free_nn}")

    # The number we are about to assign should not be connected to any existing installs as
    # an NN. Again, the above logic should do this, but we REALLY care about this not happening
    # also, if we are re-assigning a number from another install, mark it with NN Assigned to indicate
    # that this has happened
    validate_network_number_unused_and_claim_install_if_needed(free_nn, None)

    return free_nn

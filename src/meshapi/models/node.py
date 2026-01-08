import uuid
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models, transaction
from django.db.models.manager import Manager
from simple_history.models import HistoricalRecords

from meshapi.util.django_pglocks import advisory_lock
from meshapi.util.network_number import (
    NETWORK_NUMBER_MAX,
    get_next_available_network_number,
    validate_network_number_unused_and_claim_install_if_needed,
)

if TYPE_CHECKING:
    # Gate the import to avoid cycles
    from meshapi.models.building import Building
    from meshapi.models.install import Install  # noqa: F401


class Node(models.Model):
    history = HistoricalRecords()

    # This should be added automatically by django-stubs, but for some reason it's not :(
    buildings: Manager["Building"]

    class Meta:
        ordering = ["network_number"]

    class NodeStatus(models.TextChoices):
        INACTIVE = "Inactive"
        ACTIVE = "Active"
        PLANNED = "Planned"

    class NodeType(models.TextChoices):
        STANDARD = "Standard", "Standard"
        HUB = "Hub", "Hub"
        SUPERNODE = "Supernode", "Supernode"
        POP = "POP", "POP"
        AP = "AP", "AP"
        REMOTE = "Remote", "Remote"

    class NodePlacement(models.TextChoices):
        ROOFTOP = "rooftop", "Rooftop"
        BALCONY = "balcony", "Balcony"
        WINDOW = "window", "Window"
        INDOOR = "indoor", "Indoor"
        UNKNOWN = None, "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    network_number = models.IntegerField(
        unique=True,
        blank=True,
        null=True,
        validators=[MaxValueValidator(NETWORK_NUMBER_MAX)],
    )

    name = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text="The colloquial name of this node used among mesh volunteers, if applicable",
    )

    status = models.CharField(choices=NodeStatus.choices, help_text="The current status of this Node")

    type = models.CharField(
        choices=NodeType.choices,
        help_text="The type of node this is, controls the icon used on the network map",
        default=NodeType.STANDARD,
    )

    latitude = models.FloatField(
        help_text="Approximate Node latitude in decimal degrees (this will match one of the attached "
        "Building objects in most cases, but has been manually moved around in some cases to "
        "more accurately reflect node location)"
    )
    longitude = models.FloatField(
        help_text="Approximate Node longitude in decimal degrees (this will match one of the attached "
        "Building objects in most cases, but has been manually moved around in some cases to "
        "more accurately reflect node location)"
    )
    altitude = models.FloatField(
        blank=True,
        null=True,
        help_text='Approximate Node altitude in "absolute" meters above mean sea level (this will '
        "match one of the attached Building objects in most cases, but has been manually moved "
        "around in some cases to more accurately reflect node location)",
    )

    install_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The date the first Install or Device associated with this Node became active on the mesh",
    )
    abandon_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The date the last Install or Device associated with this Node was abandoned, "
        "unplugged, or removed from service",
    )

    placement = models.CharField(
        choices=NodePlacement.choices,
        help_text="The placement of the node within the building it is located on",
        default=NodePlacement.UNKNOWN,
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="A free-form text description of this Node, to track any additional information. "
        "For Nodes imported from the spreadsheet, this starts with a formatted block of information about the import "
        "process and original spreadsheet data. However this structure can be changed by admins at any time and "
        "should not be relied on by automated systems. ",
    )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.network_number and self.status == self.NodeStatus.ACTIVE:
            # If the Node has been set to active (or newly created as active) but
            # no network number has been set, we use our nn assignment logic to pick one automatically,
            # because we don't want active nodes that don't have network numbers
            # (this makes no sense and volunteers would be very confused)
            with transaction.atomic():
                with advisory_lock("nn_assignment_lock"):
                    self.network_number = get_next_available_network_number()
                    return super().save(*args, **kwargs)

        if not self._state.adding:
            # Network numbers are immutable. Double check that nobody is trying to change the NN of this existing node
            # while technically we might be able to allow this, we would need to be very careful about edge caases with
            # devices, install number matching, etc. It's much safer and simplier to force admins that want to change
            # a network number to do so by creating a new node object
            original = Node.objects.get(pk=self.pk)
            if original.network_number is not None and self.network_number != original.network_number:
                raise ValidationError("Network number is immutable once set")

        if not self.network_number:
            # If we don't have a network number, short circuit the below logic as it is focused on validating them
            # we are almost certainly a pending or inactive node, and not ready for that validation yet
            return super().save(*args, **kwargs)

        # In all other cases, we have a new network number (either new to this object, or the object is entirely
        # new to the database), since this could be a "vanity" NN assignment and the user could have typed
        # anything they want into the admin form we need to validate that  it is valid before we save, so we call
        # into a helper function in the NN assignment logic to check that this is a good network number, and update
        # the corresponding install object if needed
        with transaction.atomic():
            validate_network_number_unused_and_claim_install_if_needed(self.network_number, self.id)
            return super().save(*args, **kwargs)

    def __str__(self) -> str:
        output = []
        if self.network_number:
            output.append(f"NN{self.network_number}")

        if self.name:
            if output:
                output.append(f"({self.name})")
            else:
                output.append(self.name)

        if output:
            return " ".join(output)
        else:
            return f"Node ID {self.id}"

    def __network_number__(self) -> str:
        if self.network_number:
            return f"NN{str(self.network_number)}"
        else:
            return "-"

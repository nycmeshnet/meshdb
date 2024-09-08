import uuid
from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models, transaction
from django.db.models.manager import Manager

from meshapi.util.django_pglocks import advisory_lock
from meshapi.util.network_number import NETWORK_NUMBER_MAX, get_next_available_network_number

if TYPE_CHECKING:
    # Gate the import to avoid cycles
    from meshapi.models.building import Building
    from meshapi.models.install import Install  # noqa: F401


class Node(models.Model):
    # This should be added automatically by django-stubs, but for some reason it's not :(
    buildings: Manager["Building"]

    class Meta:
        ordering = ["network_number"]

    class NodeStatus(models.TextChoices):
        INACTIVE = "Inactive"
        ACTIVE = "Active"
        PLANNED = "Planned"

    class NodeType(models.TextChoices):
        STANDARD = "Standard"
        HUB = "Hub"
        SUPERNODE = "Supernode"
        POP = "POP"
        AP = "AP"
        REMOTE = "Remote"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    network_number = models.IntegerField(
        unique=True,
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
            with transaction.atomic():
                with advisory_lock("nn_assignment_lock"):
                    self.network_number = get_next_available_network_number()
                    super().save(*args, **kwargs)
        else:
            if not self._state.adding:
                original = Node.objects.get(pk=self.pk)
                if original.network_number is not None and self.network_number != original.network_number:
                    raise ValidationError("Network number is immutable once set")

            if self.network_number:
                pre_existing_node_with_nn = Node.objects.filter(network_number=self.network_number).first()
                if pre_existing_node_with_nn is not None and pre_existing_node_with_nn != self:
                    raise ValidationError("Network number already in use by another node")

                if not TYPE_CHECKING:
                    Install = apps.get_model(app_label="meshapi", model_name="Install")  # noqa: F811
                    install_for_nn: Install = Install.objects.filter(  # type: ignore
                        install_number=self.network_number
                    ).first()
                    if install_for_nn and install_for_nn.node != self:
                        if install_for_nn.status == Install.InstallStatus.ACTIVE:
                            raise ValidationError("Active install number cannot be reused as a network number")

                        if install_for_nn.status != Install.InstallStatus.NN_REASSIGNED:
                            install_for_nn.status = Install.InstallStatus.NN_REASSIGNED
                            install_for_nn.save()

            super().save(*args, **kwargs)

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

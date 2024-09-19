import uuid
from typing import Any, Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import IntegerField

from .building import Building
from .member import Member
from .node import Node
from .util.auto_incrementing_integer_field import AutoIncrementingIntegerField


class Install(models.Model):
    class Meta:
        permissions = [
            ("assign_nn", "Can assign an NN to install"),
            ("update_panoramas", "Can update panoramas"),
        ]
        ordering = ["-install_number"]

    class InstallStatus(models.TextChoices):
        REQUEST_RECEIVED = "Request Received"
        PENDING = "Pending"
        BLOCKED = "Blocked"
        ACTIVE = "Active"
        INACTIVE = "Inactive"
        CLOSED = "Closed"
        NN_REASSIGNED = "NN Reassigned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Install Number (generated when form is submitted)
    # We use a custom field to ensure that mark this column as "GENERATED BY DEFAULT AS IDENTITY"
    # in the SQL DDL which causes this field to autopopulate at the DB level
    install_number = AutoIncrementingIntegerField(unique=True, null=False, editable=False)

    node = models.ForeignKey(
        Node,
        blank=True,
        null=True,
        related_name="installs",
        on_delete=models.PROTECT,
        help_text="The node this install is associated with. This node's network_number field "
        "corresponds to the static IP address and OSPF ID of the router this install utilizes, "
        "the DHCP range it receives an address from, etc.",
    )

    # Summary status of install
    status = models.CharField(
        choices=InstallStatus.choices,
        help_text="The current status of this install",
    )

    # OSTicket Ticket Number
    ticket_number = models.CharField(
        blank=True,
        null=True,
        help_text="The ticket number of the OSTicket used to track communications with the member about "
        "this install. Note that although this appears to be an integer, it is not. Leading zeros"
        "are important, so this should be stored as a string at all times",
    )

    # Important dates
    request_date = models.DateField(help_text="The date that this install request was received")
    install_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The date this install was completed and deployed to the mesh",
    )
    abandon_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The date this install was abandoned, unplugged, or disassembled",
    )

    # Relation to Building
    building = models.ForeignKey(
        Building,
        on_delete=models.PROTECT,
        related_name="installs",
        help_text="The building where the install is located. In the case of a structure with multiple buildings, "
        "this will be the building whose address makes sense for this install's unit.",
    )
    unit = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text="Line 2 of this install's mailing address",
    )
    roof_access = models.BooleanField(
        default=False,
        help_text="True if the member indicated they had access to the roof when they submitted the join form",
    )

    # Relation to Member
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="installs",
        help_text="The member this install is associated with",
    )
    referral = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text='The "How did you hear about us?" information provided to us when the member submitted the join form',
    )
    notes = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="A free-form text description of this Install, to track any additional information. "
        "For Installs imported from the spreadsheet, this starts with a formatted block of information about the "
        "import process and original spreadsheet data. However this structure can be changed by admins at any time "
        "and should not be relied on by automated systems. ",
    )
    diy = models.BooleanField(
        default=None,
        blank=True,
        null=True,
        verbose_name="Is DIY?",
        help_text="Was this install conducted by the member themselves? "
        "If not, it was done by a volunteer installer on their behalf",
    )

    @property
    def network_number(self) -> IntegerField | Optional[int]:
        return self.node.network_number if self.node else None

    def __str__(self) -> str:
        return f"#{str(self.install_number)}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            original = Install.objects.get(pk=self.pk)
            if self.install_number != original.install_number:
                raise ValidationError("Install number is immutable")

        super().save(*args, **kwargs)

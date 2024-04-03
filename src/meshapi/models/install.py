from django.db import models

from .building import Building
from .member import Member
from .node import Node


class Install(models.Model):
    class InstallStatus(models.TextChoices):
        REQUEST_RECEIVED = "Request Received"
        PENDING = "Pending"
        BLOCKED = "Blocked"
        ACTIVE = "Active"
        INACTIVE = "Inactive"
        CLOSED = "Closed"
        NN_REASSIGNED = "NN Reassigned"

    # Install Number (generated when form is submitted)
    install_number = models.AutoField(
        primary_key=True,
        db_column="install_number",
    )

    node = models.ForeignKey(
        Node,
        blank=True,
        null=True,
        db_column="network_number",
        related_name="installs",
        on_delete=models.PROTECT,
        help_text="The node this install is associated with, the integer value of this field is "
        "also the network number, which corresponds to the static IP address and OSPF ID of the "
        "router this install utilizes, the DHCP range it receives an address from, etc.",
    )

    # Summary status of install
    status = models.CharField(
        choices=InstallStatus.choices,
        help_text="The current status of this install",
    )

    # OSTicket ID
    ticket_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="The ID of the OSTicket used to track communications with the member about this install",
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
        "For Installs imported from the spreadsheet, this starts with a formatted block of information about the import process"
        "and original spreadsheet data. However this structure can be changed by admins at any time and should not be relied on"
        "by automated systems. ",
    )
    diy = models.BooleanField(
        default=None,
        blank=True,
        null=True,
        verbose_name="Is DIY?",
        help_text="Was this install conducted by the member themselves? "
        "If not, it was done by a volunteer installer on their behalf",
    )

    class Meta:
        permissions = [
            ("assign_nn", "Can assign an NN to install"),
            ("update_panoramas", "Can update panoramas"),
        ]

    def __str__(self):
        return f"#{str(self.install_number)}"

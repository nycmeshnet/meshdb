import datetime
import uuid
from typing import Optional

from django.db import models
from simple_history.models import HistoricalRecords

from meshapi.models.devices.device import Device


class Link(models.Model):
    history = HistoricalRecords()

    class LinkStatus(models.TextChoices):
        INACTIVE = "Inactive"
        PLANNED = "Planned"
        ACTIVE = "Active"

    class LinkType(models.TextChoices):
        FIVE_GHZ = "5 GHz"
        TWENTYFOUR_GHZ = "24 GHz"
        SIXTY_GHZ = "60 GHz"
        SEVENTY_EIGHTY_GHZ = "70-80 GHz"
        VPN = "VPN"
        FIBER = "Fiber"
        ETHERNET = "Ethernet"

    class Meta:
        ordering = ["id"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    from_device = models.ForeignKey(
        Device,
        on_delete=models.PROTECT,
        related_name="links_from",
        help_text="The device on one side of this network link, from/to are not meaningful except to disambiguate",
    )
    to_device = models.ForeignKey(
        Device,
        on_delete=models.PROTECT,
        related_name="links_to",
        help_text="The device on one side of this network link, from/to are not meaningful except to disambiguate",
    )

    status = models.CharField(choices=LinkStatus.choices, help_text="The current status of this link")
    type = models.CharField(
        choices=LinkType.choices,
        default=None,
        blank=True,
        null=True,
        help_text="The technology used for this link 5Ghz, 60Ghz, fiber, etc.",
    )

    install_date = models.DateField(default=None, blank=True, null=True, help_text="The date this link was created")
    abandon_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The date this link was powered off, disassembled, or abandoned",
    )

    description = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text='A short description of "where to where" this link connects in human readable language',
    )
    notes = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="A free-form text description of this Link, to track any additional information.",
    )

    uisp_id = models.CharField(
        default=None, blank=True, null=True, help_text="The UUID used to indentify this link in UISP (if applicable)"
    )

    def __str__(self) -> str:
        from_name = None
        to_name = None

        if self.to_device.node == self.from_device.node:
            from_name = self.from_device.name
            to_name = self.to_device.name

        if not from_name and self.from_device.node.network_number:
            from_name = f"NN{self.from_device.node.network_number}"

        if not to_name and self.to_device.node.network_number:
            to_name = f"NN{self.to_device.node.network_number}"

        if from_name and to_name:
            return f"{from_name} ↔ {to_name}"

        return f"MeshDB Link ID {self.id}"

    @property
    def last_functioning_date_estimate(self) -> Optional[datetime.date]:
        """Estimate the most recent date that we can guarantee this link was functional"""

        # Active and pending links are assumed to currently be functional
        if self.status != Link.LinkStatus.INACTIVE:
            return datetime.date.today()

        # For inactive links, we use the abandon date if we have it
        # (since the link was likely functional on or around this date)
        if self.abandon_date:
            return self.abandon_date

        # If we don't have an abandon date, but we do have an installation date,
        # use that as the estimate instead
        if self.install_date:
            return self.install_date

        # If we don't have an install date or an abandon date,
        # we can't really make an estimate, so we return none
        return None

from django.db import models

from meshapi.models.devices.device import Device


class Link(models.Model):
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
        if self.from_device.node.network_number and self.to_device.node.network_number:
            return f"NN{self.from_device.node.network_number} → NN{self.to_device.node.network_number}"
        return f"MeshDB Link ID {self.id}"

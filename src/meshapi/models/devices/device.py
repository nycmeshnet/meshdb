from django.db import models

from meshapi.models.node import Node


class Device(models.Model):
    class DeviceStatus(models.TextChoices):
        INACTIVE = "Inactive"
        ACTIVE = "Active"
        POTENTIAL = "Potential"

    class DeviceType(models.TextChoices):
        AP = "ap"
        GATEWAY = "gateway"
        GPON = "gpon"
        CONVERTOR = "convertor"
        OTHER = "other"
        PTP = "ptp"
        ROUTER = "router"
        SERVER = "server"
        STATION = "station"
        SWITCH = "switch"
        UPS = "ups"
        WIRELESS = "wireless"
        HOMEWIFI = "homeWiFi"
        WIRELESSDEVICE = "wirelessDevice"

    node = models.ForeignKey(
        Node,
        related_name="devices",
        db_column="network_number",
        on_delete=models.PROTECT,
        help_text="The logical node this Device is located within. The integer value of this field is "
        "also the network number, which corresponds to the static IP address and OSPF ID of this device "
        "or the DHCP range it receives an address from. This number is also usually found in the device name",
    )

    name = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text="The colloquial name of this node used among mesh volunteers, if applicable",
    )

    model = models.CharField(
        help_text="The manufacturer model name of this device, e.g. OmniTik or LBEGen2",
    )

    type = models.CharField(
        choices=DeviceType.choices,
        help_text="The general type of device that this is, the role it fills on the mesh. e.g. ap, ptp, station, etc. "
        "This lines up with the UISP 'role' property",
    )
    status = models.CharField(choices=DeviceStatus.choices, help_text="The current status of this device")

    latitude = models.FloatField(
        help_text="Approximate Device latitude in decimal degrees (this will match the attached "
        "Node object in most cases, but has been manually moved around in some cases to "
        "more accurately reflect the device location)"
    )
    longitude = models.FloatField(
        help_text="Approximate Device longitude in decimal degrees (this will match the attached "
        "Node object in most cases, but has been manually moved around in some cases to "
        "more accurately reflect the device location)"
    )
    altitude = models.FloatField(
        blank=True,
        null=True,
        help_text='Approximate Device altitude in "absolute" meters above mean sea level (this '
        "will match the attached Node object in most cases, but has been manually moved around in "
        "some cases to more accurately reflect the device location)",
    )

    install_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The date this device first became active on the mesh",
    )
    abandon_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The this device was abandoned, unplugged, or removed from service",
    )

    notes = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="A free-form text description of this Device, to track any additional information. "
        "For imported Devices, this starts with a formatted block of information about the import process"
        "and original data. However this structure can be changed by admins at any time and should not be relied on"
        "by automated systems. ",
    )

    uisp_id = models.CharField(
        default=None, blank=True, null=True, help_text="The UUID used to indentify this device in UISP (if applicable)"
    )

    ssid = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text="The SSID being broadcast by this device",
    )

    ip_address = models.GenericIPAddressField(
        default=None,
        blank=True,
        null=True,
        help_text="The IP address of this device within the 10.x network",
        protocol="ipv4",
    )

    def __str__(self):
        if self.name:
            return self.name
        return f"MeshDB Device ID {self.id}"

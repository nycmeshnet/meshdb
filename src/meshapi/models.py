from typing import List

from django.contrib.auth.models import Group, Permission
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.fields import EmailField
from django.db.models.signals import pre_save
from django.dispatch import receiver

from meshdb.utils.spreadsheet_import.building.constants import AddressTruthSource

NETWORK_NUMBER_MIN = 101
NETWORK_NUMBER_MAX = 8192


class Node(models.Model):
    class NodeStatus(models.TextChoices):
        INACTIVE = "Inactive"
        ACTIVE = "Active"
        PLANNED = "Planned"

    network_number = models.AutoField(
        primary_key=True,
        db_column="network_number",
        validators=[MaxValueValidator(NETWORK_NUMBER_MAX)],
    )

    name = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text="The colloquial name of this node used among mesh volunteers, if applicable",
    )

    status = models.CharField(choices=NodeStatus.choices, help_text="The current status of this Node")

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
        "For Nodes imported from the spreadsheet, this starts with a formatted block of information about the import process"
        "and original spreadsheet data. However this structure can be changed by admins at any time and should not be relied on"
        "by automated systems. ",
    )

    def __str__(self):
        if self.name:
            return str(self.name)

        return f"NN{str(self.network_number)}"


class Building(models.Model):
    """
    A building represents a single discrete place represented by street address. This may be located
    within a larger structure with multiple street addresses.

    If located within NYC, this will usually have a BIN number. However, this BIN number is not
    necessarily unique. In the case of a structure with multiple street addresses, we create a
    "Building" object for each address, but these "Building" objects will all share a BIN.
    """

    bin = models.IntegerField(
        blank=True,
        null=True,
        help_text="NYC DOB Identifier for the structure containing this building",
        validators=[MinValueValidator(0)],
    )

    street_address = models.CharField(
        blank=True, null=True, help_text="Line 1 only of the address of this building: i.e. <house num> <street>"
    )
    city = models.CharField(
        blank=True,
        null=True,
        help_text="The name of the borough this building is in for buildings within NYC, "
        '"New York" for Manhattan to match street addresses. The actual city name for anything outside NYC',
    )
    state = models.CharField(
        blank=True,
        null=True,
        help_text='The 2 letter abreviation of the US State this building is contained within, e.g. "NY" or "NJ"',
    )
    zip_code = models.CharField(
        blank=True, null=True, help_text="The five digit ZIP code this building is contained within"
    )

    address_truth_sources = ArrayField(
        models.CharField(
            choices=list((src.value, src.name) for src in AddressTruthSource),
        ),
        help_text="A list of strings that answers the question: How did we determine the content of "
        "the street address, city, state, and ZIP fields? This is useful in understanding the level of validation "
        "applied to spreadsheet imported data. Possible values are: "
        f"{', '.join(src.value for src in AddressTruthSource)}. Check the import script for details",
    )

    latitude = models.FloatField(help_text="Building latitude in decimal degrees")
    longitude = models.FloatField(help_text="Building longitude in decimal degrees")
    altitude = models.FloatField(
        blank=True, null=True, help_text='Building rooftop altitude in "absolute" meters above mean sea level'
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="A free-form text description of this building, to track any additional information. "
        "For Buidings imported from the spreadsheet, this starts with a formatted block of information about the import process"
        "and original spreadsheet data. However this structure can be changed by admins at any time and should not be relied on"
        "by automated systems. ",
    )

    primary_node = models.ForeignKey(
        Node,
        on_delete=models.PROTECT,
        related_name="+",  # Don't allow reverse access, since this will be included via nodes below
        help_text="The primary node for this Building, for cases where it has more than one. This is the node "
        "bearing the network number that the building is collquially referred to by volunteers and is "
        "usually the first NN held by any equipment on the building. If present, this must also be included in nodes",
        blank=True,
        null=True,
    )
    nodes = models.ManyToManyField(
        Node,
        help_text="All nodes located on the same structure (i.e. a discrete man-made place identified by the same BIN) "
        "that this Building is located within.",
        related_name="buildings",
    )

    def save(self, *args, **kwargs):
        # Ensure primary_node is always contained in nodes
        if self.primary_node and self.primary_node not in self.nodes.all():
            self.nodes.add(self.primary_node)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.street_address:
            addr_str = str(self.street_address)
            if self.city:
                addr_str += f", {self.city}"
            if self.state:
                addr_str += f", {self.state}"
            return addr_str
        if self.bin:
            return f"BIN {self.bin}"
        return f"MeshDB Building ID {self.id}"


class Member(models.Model):
    name = models.CharField(help_text='Member full name in the format: "First Last"')
    primary_email_address = models.EmailField(null=True, help_text="Primary email address used to contact the member")
    stripe_email_address = models.EmailField(
        null=True,
        blank=True,
        default=None,
        help_text="Email address used by the member to donate via Stripe, if different to their primary email",
    )
    additional_email_addresses = ArrayField(
        EmailField(),
        null=True,
        blank=True,
        default=list,
        help_text="Any additional email addresses associated with this member",
    )
    phone_number = models.CharField(
        default=None, blank=True, null=True, help_text="A contact phone number for this member"
    )
    slack_handle = models.CharField(default=None, blank=True, null=True, help_text="The member's slack handle")
    notes = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="A free-form text description of how to contact this member, to track any additional information. "
        "For Members imported from the spreadsheet, this starts with a formatted block of information about the import process"
        "and original spreadsheet data. However this structure can be changed by admins at any time and should not be relied on"
        "by automated systems. ",
    )

    def __str__(self):
        if self.name:
            return self.name
        return f"MeshDB Member ID {self.id}"

    @property
    def all_email_addresses(self) -> List[str]:
        all_emails = []
        if self.primary_email_address and self.primary_email_address not in all_emails:
            all_emails.append(self.primary_email_address)

        if self.stripe_email_address and self.stripe_email_address not in all_emails:
            all_emails.append(self.stripe_email_address)

        if self.additional_email_addresses:
            for email in self.additional_email_addresses:
                if email not in all_emails:
                    all_emails.append(email)

        return all_emails


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
        ]

    def __str__(self):
        return f"#{str(self.install_number)}"


class Device(models.Model):
    class DeviceStatus(models.TextChoices):
        INACTIVE = "Inactive"
        ACTIVE = "Active"

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

    model_name = models.CharField(
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

    def __str__(self):
        if self.name:
            return self.name
        return f"MeshDB Device ID {self.id}"


class Link(models.Model):
    class LinkStatus(models.TextChoices):
        INACTIVE = "Inactive"
        PLANNED = "Planned"
        ACTIVE = "Active"

    class LinkType(models.TextChoices):
        STANDARD = "Standard"
        VPN = "VPN"
        MMWAVE = "MMWave"
        FIBER = "Fiber"

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

    def __str__(self):
        if self.from_device.node.network_number and self.to_device.node.network_number:
            return f"NN{self.from_device.node.network_number} → NN{self.to_device.node.network_number}"
        return f"MeshDB Link ID {self.id}"


class Sector(Device):
    radius = models.FloatField(
        help_text="The radius to display this sector on the map (in km)",
        validators=[MinValueValidator(0)],
    )
    azimuth = models.IntegerField(
        help_text="The compass heading that this sector is pointed towards",
        validators=[
            MinValueValidator(0),
            MaxValueValidator(360),
        ],
    )
    width = models.IntegerField(
        help_text="The approximate width of the beam this sector produces",
        validators=[
            MinValueValidator(0),
            MaxValueValidator(360),
        ],
    )

    ssid = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text="The SSID being broadcast by this device",
    )

    def __str__(self):
        if self.ssid:
            return self.ssid
        return f"MeshDB Sector ID {self.id}"

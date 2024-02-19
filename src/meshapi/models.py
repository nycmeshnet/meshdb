from typing import List

from django.contrib.auth.models import Group, Permission
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.fields import EmailField

from meshdb.utils.spreadsheet_import.building.constants import AddressTruthSource

NETWORK_NUMBER_MIN = 101
NETWORK_NUMBER_MAX = 8192


class Building(models.Model):
    class BuildingStatus(models.TextChoices):
        INACTIVE = "Inactive"
        ACTIVE = "Active"

    bin = models.IntegerField(
        blank=True,
        null=True,
        help_text="NYC DOB Identifier for this building",
        validators=[MinValueValidator(0)],
    )
    building_status = models.TextField(
        choices=BuildingStatus.choices,
        help_text="Current building status. Active indicates this is a building with active mesh equipment, "
        "regardless of if there are any members connected via active installs",
    )
    street_address = models.TextField(
        blank=True, null=True, help_text="Line 1 only of the address of this building: i.e. <house num> <street>"
    )
    city = models.TextField(
        blank=True,
        null=True,
        help_text="The name of the borough this building is in for buildings within NYC, "
        '"New York" for Manhattan to match street addresses. The actual city name for anything outside NYC',
    )
    state = models.TextField(
        blank=True,
        null=True,
        help_text='The 2 letter abreviation of the US State this building is contained within, e.g. "NY" or "NJ"',
    )
    zip_code = models.TextField(
        blank=True, null=True, help_text="The five digit ZIP code this building is contained within"
    )
    invalid = models.BooleanField(
        default=False,
        help_text="Is the location of this building specified sufficiently enough to be considered valid? "
        "This means the building must have a non-null street address, city, state, and zip. "
        "Some old spreadsheet imports are missing some of this information, and this field is useful for filtering these out",
    )
    address_truth_sources = models.TextField(
        help_text="A comma separated list of strings that answers the question: How did we determine the content of "
        "the street address, city, state, and ZIP fields? This is useful in understanding the level of validation "
        "applied to spreadsheet imported data. Possible values are: "
        f"{', '.join(src.value for src in AddressTruthSource)}. Check the import script for details"
    )
    latitude = models.FloatField(help_text="Building latitude in decimal degrees")
    longitude = models.FloatField(help_text="Building longitude in decimal degrees")
    altitude = models.FloatField(
        blank=True, null=True, help_text='Building rooftop altitude in "absolute" meters above sea level'
    )
    primary_nn = models.IntegerField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(NETWORK_NUMBER_MIN),
            MaxValueValidator(NETWORK_NUMBER_MAX),
        ],
        help_text="The primary network number of this building, for nearly all buildings "
        "this will be the same value attached to all installs. In rare cases where "
        'buildings have more that one NN, this is the "primary" one, indicating what '
        "this building should be referred to as (this should match the core router)",
    )
    node_name = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="The colloquial name of this node used among mesh volunteers, if applicable",
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="A free-form text description of this building, to track any additional information. "
        "For Buidings imported from the spreadsheet, this starts with a formatted block of information about the import process"
        "and original spreadsheet data. However this structure can be changed by admins at any time and should not be relied on"
        "by automated systems. ",
    )

    def __str__(self):
        if self.node_name:
            return str(self.node_name)
        if self.street_address:
            return str(self.street_address)
        if self.bin:
            return f"BIN {self.bin}"
        return f"MeshDB Building ID {self.id}"


class Member(models.Model):
    name = models.TextField(help_text='Member full name in the format: "First Last"')
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
    phone_number = models.TextField(
        default=None, blank=True, null=True, help_text="A contact phone number for this member"
    )
    slack_handle = models.TextField(default=None, blank=True, null=True, help_text="The member's slack handle")
    invalid = models.BooleanField(
        default=False,
        help_text="Is there enough information about how to contact "
        "this member for this object to be considered valid? This mostly means the member must have a non-null primary email address. "
        "Some old spreadsheet imports are missing this information, and this field is useful for filtering these out",
    )
    contact_notes = models.TextField(
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

    # The NN this install is associated with.
    # Through this, a building can have multiple NNs
    network_number = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(NETWORK_NUMBER_MIN), MaxValueValidator(NETWORK_NUMBER_MAX)],
        help_text="The network number associated with this install, this corresponds to "
        "the static IP address and OSPF ID of the router this install utilizes, the DHCP range it "
        "receives an address from, etc.",
    )

    # Summary status of install
    install_status = models.TextField(
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
        help_text="The building where the install is located",
    )
    unit = models.TextField(
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


class Link(models.Model):
    class LinkStatus(models.TextChoices):
        DEAD = "Dead"
        PLANNED = "Planned"
        ACTIVE = "Active"

    class LinkType(models.TextChoices):
        STANDARD = "Standard"
        VPN = "VPN"
        MMWAVE = "MMWave"
        FIBER = "Fiber"

    from_building = models.ForeignKey(
        Building,
        on_delete=models.PROTECT,
        related_name="links_from",
        help_text="The building on one side of this network link, from/to are not meaningful except to disambiguate",
    )
    to_building = models.ForeignKey(
        Building,
        on_delete=models.PROTECT,
        related_name="links_to",
        help_text="The building on one side of this network link, from/to are not meaningful except to disambiguate",
    )

    status = models.TextField(choices=LinkStatus.choices, help_text="The current status of this link")
    type = models.TextField(
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

    description = models.TextField(
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
        if self.from_building.primary_nn and self.to_building.primary_nn:
            return f"NN{self.from_building.primary_nn} → NN{self.to_building.primary_nn}"
        return f"MeshDB Link ID {self.id}"


class Sector(models.Model):
    class SectorStatus(models.TextChoices):
        ABANDONED = "Abandoned"
        ACTIVE = "Active"
        POTENTIAL = "Potential"

    building = models.ForeignKey(
        Building,
        on_delete=models.PROTECT,
        related_name="sectors",
        help_text="The building this sector is installed on",
    )
    name = models.TextField(
        help_text="The name of the hub sector is installed on",
    )

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

    status = models.TextField(choices=SectorStatus.choices, help_text="The current status of this Sector")

    install_date = models.DateField(default=None, blank=True, null=True, help_text="The date this Sector was installed")
    abandon_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The date this Sector was powered off, disassembled, or abandoned",
    )

    device_name = models.TextField(
        help_text="The name of the device/antenna being used to provide this sector of coverage"
    )
    ssid = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="The SSID being broadcast by this device",
    )

    notes = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="A free-form text description of this Sector, to track any additional information. "
        "The structure of this data can be changed by admins at any time and should not be relied on "
        "by automated systems. ",
    )

    def __str__(self):
        if self.ssid:
            return self.ssid
        return f"MeshDB Sector ID {self.id}"

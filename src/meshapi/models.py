from django.contrib.auth.models import Group, Permission
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.fields import EmailField

NETWORK_NUMBER_MIN = 101
NETWORK_NUMBER_MAX = 8192


class Building(models.Model):
    class BuildingStatus(models.TextChoices):
        INACTIVE = "Inactive"
        ACTIVE = "Active"

    bin = models.IntegerField(blank=True, null=True)
    building_status = models.TextField(choices=BuildingStatus.choices)
    street_address = models.TextField(blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    state = models.TextField(blank=True, null=True)
    zip_code = models.TextField(blank=True, null=True)
    invalid = models.BooleanField(default=False)
    address_truth_sources = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.FloatField(blank=True, null=True)
    primary_nn = models.IntegerField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(NETWORK_NUMBER_MIN),
            MaxValueValidator(NETWORK_NUMBER_MAX),
        ],
    )
    node_name = models.TextField(default=None, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.node_name:
            return str(self.node_name)
        if self.street_address:
            return str(self.street_address)
        if self.bin:
            return f"BIN {self.bin}"
        return f"MeshDB Building ID {self.id}"


class Member(models.Model):
    name = models.TextField()
    email_address = models.EmailField(null=True)
    stripe_email_address = models.EmailField(null=True, blank=True, default=None)
    secondary_emails = ArrayField(EmailField(), null=True, blank=True, default=list)
    phone_number = models.TextField(default=None, blank=True, null=True)
    slack_handle = models.TextField(default=None, blank=True, null=True)
    invalid = models.BooleanField(default=False)
    contact_notes = models.TextField(default=None, blank=True, null=True)

    def __str__(self):
        if self.name:
            return self.name
        return f"MeshDB Member ID {self.id}"


class Install(models.Model):
    class InstallStatus(models.TextChoices):
        REQUEST_RECEIVED = "Request Received"
        PENDING = "Pending"
        BLOCKED = "Blocked"
        ACTIVE = "Active"
        INACTIVE = "Inactive"
        CLOSED = "Closed"

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
    )

    # Summary status of install
    install_status = models.TextField(choices=InstallStatus.choices)

    # OSTicket ID
    ticket_id = models.IntegerField(blank=True, null=True)

    # Important dates
    request_date = models.DateField()
    install_date = models.DateField(default=None, blank=True, null=True)
    abandon_date = models.DateField(default=None, blank=True, null=True)

    # Relation to Building
    building = models.ForeignKey(Building, on_delete=models.PROTECT)
    unit = models.TextField(default=None, blank=True, null=True)
    roof_access = models.BooleanField(default=False)

    # Relation to Member
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    referral = models.TextField(default=None, blank=True, null=True)
    notes = models.TextField(default=None, blank=True, null=True)

    class Meta:
        permissions = [
            ("assign_nn", "Can assign an NN to install"),
        ]

    def __str__(self):
        return f"Install #{str(self.install_number)}"


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

    from_building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="link_from")
    to_building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="link_to")

    status = models.TextField(choices=LinkStatus.choices)
    type = models.TextField(choices=LinkType.choices, default=None, blank=True, null=True)

    install_date = models.DateField(default=None, blank=True, null=True)
    abandon_date = models.DateField(default=None, blank=True, null=True)

    description = models.TextField(default=None, blank=True, null=True)
    notes = models.TextField(default=None, blank=True, null=True)


class Sector(models.Model):
    class SectorStatus(models.TextChoices):
        ABANDONED = "Abandoned"
        ACTIVE = "Active"
        POTENTIAL = "Potential"

    building = models.ForeignKey(Building, on_delete=models.PROTECT)
    name = models.TextField()

    radius = models.FloatField(
        validators=[MinValueValidator(0)],
    )
    azimuth = models.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(360),
        ],
    )
    width = models.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(360),
        ],
    )

    status = models.TextField(choices=SectorStatus.choices)

    install_date = models.DateField(default=None, blank=True, null=True)
    abandon_date = models.DateField(default=None, blank=True, null=True)

    device_name = models.TextField()
    ssid = models.TextField(default=None, blank=True, null=True)

    notes = models.TextField(default=None, blank=True, null=True)

from typing import List

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
    primary_email_address = models.EmailField(null=True)
    stripe_email_address = models.EmailField(null=True, blank=True, default=None)
    additional_email_addresses = ArrayField(EmailField(), null=True, blank=True, default=list)
    phone_number = models.TextField(default=None, blank=True, null=True)
    slack_handle = models.TextField(default=None, blank=True, null=True)
    invalid = models.BooleanField(default=False)
    contact_notes = models.TextField(default=None, blank=True, null=True)

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

    # Summary status of install
    status = models.TextField(choices=InstallStatus.choices)

    # OSTicket ID
    ticket_id = models.IntegerField(blank=True, null=True)

    # Important dates
    request_date = models.DateField()
    install_date = models.DateField(default=None, blank=True, null=True)
    abandon_date = models.DateField(default=None, blank=True, null=True)

    # Relation to Building
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="installs")
    unit = models.TextField(default=None, blank=True, null=True)
    roof_access = models.BooleanField(default=False)

    # Relation to Member
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="installs")
    referral = models.TextField(default=None, blank=True, null=True)
    notes = models.TextField(default=None, blank=True, null=True)
    diy = models.BooleanField(default=None, blank=True, null=True, verbose_name="Is DIY?")

    class Meta:
        permissions = [
            ("assign_nn", "Can assign an NN to install"),
        ]

    def __str__(self):
        return f"#{str(self.install_number)}"

class Device(models.Model):
    class DeviceStatus(models.TextChoices):
        ABANDONED = "Abandoned"
        ACTIVE = "Active"
        POTENTIAL = "Potential"

    name = models.TextField()
    device_name = models.TextField()

    status = models.TextField(choices=DeviceStatus.choices)
    powered_by_install = models.ForeignKey(Install, on_delete=models.PROTECT, related_name="powers")

    # The NN this device is associated with.
    # Through this, a building can have multiple NNs
    network_number = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(NETWORK_NUMBER_MIN), MaxValueValidator(NETWORK_NUMBER_MAX)],
    )

    install_date = models.DateField(default=None, blank=True, null=True)
    abandon_date = models.DateField(default=None, blank=True, null=True)

    notes = models.TextField(default=None, blank=True, null=True)


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

    from_device = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="links_from")
    to_device = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="links_to")

    status = models.TextField(choices=LinkStatus.choices)
    type = models.TextField(choices=LinkType.choices, default=None, blank=True, null=True)

    install_date = models.DateField(default=None, blank=True, null=True)
    abandon_date = models.DateField(default=None, blank=True, null=True)

    description = models.TextField(default=None, blank=True, null=True)
    notes = models.TextField(default=None, blank=True, null=True)

    def __str__(self):
        if self.from_building.primary_nn and self.to_building.primary_nn:
            return f"NN{self.from_building.primary_nn} → NN{self.to_building.primary_nn}"
        return f"MeshDB Link ID {self.id}"


class Sector(Device):
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

    # XXX (willnilges): Move SSID to device?
    ssid = models.TextField(default=None, blank=True, null=True)

    def __str__(self):
        if self.ssid:
            return self.ssid
        return f"MeshDB Sector ID {self.id}"

from django.db import models

from django.contrib.auth.models import Group


class Installer(Group):
    description = models.TextField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Building(models.Model):
    class BuildingStatus(models.IntegerChoices):
        INACTIVE = 0
        ACTIVE = 1

    bin = models.IntegerField()
    building_status = models.IntegerField(choices=BuildingStatus.choices)
    street_address = models.TextField()
    city = models.TextField()
    state = models.TextField()
    zip_code = models.IntegerField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.FloatField()
    network_number = models.IntegerField(blank=True, null=True)
    install_date = models.DateField(default=None, blank=True, null=True)
    abandon_date = models.DateField(default=None, blank=True, null=True)


class Member(models.Model):
    first_name = models.TextField()
    last_name = models.TextField()
    email_address = models.EmailField()
    phone_numer = models.TextField(
        default=None, blank=True, null=True
    )  # TODO (willnilges): Can we get some validation on this?
    slack_handle = models.TextField(default=None, blank=True, null=True)


class Install(models.Model):
    class InstallStatus(models.IntegerChoices):
        PLANNED = 0
        INACTIVE = 1
        ACTIVE = 2

    install_number = models.IntegerField()
    install_status = models.IntegerField(choices=InstallStatus.choices)
    building_id = models.ForeignKey(Building, on_delete=models.PROTECT)
    unit = models.TextField(default=None, blank=True, null=True)
    member_id = models.ForeignKey(Member, on_delete=models.PROTECT)
    install_date = models.DateField(default=None, blank=True, null=True)
    abandon_date = models.DateField(default=None, blank=True, null=True)


class Request(models.Model):
    class RequestStatus(models.IntegerChoices):
        OPEN = 0
        CLOSED = 1
        INSTALLED = 2

    request_status = models.IntegerField(choices=RequestStatus.choices)
    roof_access = models.BooleanField(default=False)
    referral = models.TextField(default=None, blank=True, null=True)
    ticket_id = models.IntegerField(blank=True, null=True)
    member_id = models.ForeignKey(Member, on_delete=models.PROTECT)
    building_id = models.ForeignKey(Building, on_delete=models.PROTECT)
    unit = models.TextField(default=None, blank=True, null=True)
    install_id = models.ForeignKey(Install, on_delete=models.PROTECT, blank=True, null=True)

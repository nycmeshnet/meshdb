# Generated by Django 4.2.13 on 2024-08-06 18:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0014_remove_device_altitude_remove_device_ip_address_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessPoint",
            fields=[
                (
                    "device_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="meshapi.device",
                    ),
                ),
                (
                    "latitude",
                    models.FloatField(
                        help_text="Approximate AP latitude in decimal degrees (this will match the attached Node object in most cases, but has been manually moved around in some cases to more accurately reflect the device location)"
                    ),
                ),
                (
                    "longitude",
                    models.FloatField(
                        help_text="Approximate AP longitude in decimal degrees (this will match the attached Node object in most cases, but has been manually moved around in some cases to more accurately reflect the device location)"
                    ),
                ),
                (
                    "altitude",
                    models.FloatField(
                        blank=True,
                        help_text='Approximate AP altitude in "absolute" meters above mean sea level (this will match the attached Node object in most cases, but has been manually moved around in some cases to more accurately reflect the device location)',
                        null=True,
                    ),
                ),
            ],
            bases=("meshapi.device",),
        ),
    ]

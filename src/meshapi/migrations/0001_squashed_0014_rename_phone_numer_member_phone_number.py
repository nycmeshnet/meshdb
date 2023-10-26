# Generated by Django 4.2.5 on 2023-10-26 01:22

import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Building",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bin", models.IntegerField(default=69)),
                ("building_status", models.IntegerField(choices=[(0, "Inactive"), (1, "Active")])),
                ("street_address", models.TextField()),
                ("city", models.TextField()),
                ("state", models.TextField()),
                ("zip_code", models.IntegerField()),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("altitude", models.FloatField()),
                ("network_number", models.IntegerField(blank=True, null=True)),
                ("install_date", models.DateField(blank=True, default=None, null=True)),
                ("abandon_date", models.DateField(blank=True, default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Member",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("first_name", models.TextField()),
                ("last_name", models.TextField()),
                ("email_address", models.EmailField(max_length=254)),
                ("phone_number", models.TextField(blank=True, default=None, null=True)),
                ("slack_handle", models.TextField(blank=True, default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Install",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("install_number", models.IntegerField()),
                ("install_status", models.IntegerField(choices=[(0, "Planned"), (1, "Inactive"), (2, "Active")])),
                ("building_id", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="meshapi.building")),
                ("member_id", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="meshapi.member")),
                ("abandon_date", models.DateField(blank=True, default=None, null=True)),
                ("install_date", models.DateField(blank=True, default=None, null=True)),
                ("unit", models.TextField(blank=True, default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Installer",
            fields=[
                (
                    "group_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="auth.group",
                    ),
                ),
                ("description", models.TextField(blank=True, max_length=100)),
            ],
            bases=("auth.group",),
            managers=[
                ("objects", django.contrib.auth.models.GroupManager()),
            ],
        ),
        migrations.CreateModel(
            name="Request",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_status", models.IntegerField(choices=[(0, "Open"), (1, "Closed"), (2, "Installed")])),
                ("ticket_id", models.IntegerField(blank=True, null=True)),
                ("building_id", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="meshapi.building")),
                (
                    "install_id",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="meshapi.install"
                    ),
                ),
                ("member_id", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="meshapi.member")),
                ("roof_access", models.BooleanField(default=False)),
                ("referral", models.TextField(blank=True, default=None, null=True)),
                ("unit", models.TextField(blank=True, default=None, null=True)),
            ],
        ),
    ]

# Generated by Django 4.2.13 on 2024-07-25 01:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0010_alter_link_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="LOS",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "analysis_date",
                    models.DateField(
                        help_text="The date we conducted the analysis that concluded this LOS exists. Important since new buildings might have been built which block the LOS after this date"
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("Human Annotated", "Human Annotated"), ("Existing Link", "Existing Link")],
                        help_text="The source of information that tells us this LOS exists",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        default=None,
                        help_text="A free-form text description of this LOS, to track any additional information.",
                        null=True,
                    ),
                ),
                (
                    "from_building",
                    models.ForeignKey(
                        help_text="The building on one side of this LOS, from/to are not meaningful except to disambiguate",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="los_from",
                        to="meshapi.building",
                    ),
                ),
                (
                    "to_building",
                    models.ForeignKey(
                        help_text="The building on one side of this LOS, from/to are not meaningful except to disambiguate",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="los_to",
                        to="meshapi.building",
                    ),
                ),
            ],
            options={
                "verbose_name": "LOS",
                "verbose_name_plural": "LOSes",
            },
        ),
    ]

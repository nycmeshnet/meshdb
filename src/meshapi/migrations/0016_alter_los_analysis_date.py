# Generated by Django 4.2.13 on 2024-08-18 22:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0015_accesspoint"),
    ]

    operations = [
        migrations.AlterField(
            model_name="los",
            name="analysis_date",
            field=models.DateField(
                blank=True,
                default=None,
                help_text="The date we conducted the analysis that concluded this LOS exists. Important since new buildings might have been built which block the LOS after this date",
                null=True,
            ),
        ),
    ]

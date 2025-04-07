# Generated by Django 4.2.17 on 2025-01-08 01:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("meshapi", "0004_alter_historicalinstall_status_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="install",
            options={
                "ordering": ["-install_number"],
                "permissions": [
                    ("assign_nn", "Can assign an NN to install"),
                    ("disambiguate_number", "Can disambiguate an install number from an NN"),
                    ("update_panoramas", "Can update panoramas"),
                ],
            },
        ),
    ]

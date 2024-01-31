# Generated by Django 4.2.9 on 2024-01-31 03:31

from django.db import migrations, models


def migrate_install_status(apps, _):
    Install = apps.get_model("meshapi", "Install")

    old_to_new_status_mapping = {
        "Open": "Pending",
        "Scheduled": "Pending",
        "NN Assigned": "Inactive",
        "Blocked": "Blocked",
        "Active": "Active",
        "Inactive": "Inactive",
        "Closed": "Closed",
    }

    for install in Install.objects.all():
        install.install_status = old_to_new_status_mapping[install.install_status_old]
        install.save()


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0004_alter_install_options"),
    ]

    operations = [
        migrations.RenameField(
            model_name="install",
            old_name="install_status",
            new_name="install_status_old",
        ),
        migrations.AddField(
            model_name="install",
            name="install_status",
            field=models.TextField(
                choices=[
                    ("Request Received", "Request Received"),
                    ("Pending", "Pending"),
                    ("Blocked", "Blocked"),
                    ("Active", "Active"),
                    ("Inactive", "Inactive"),
                    ("Closed", "Closed"),
                ],
                default="Request Received",
            ),
        ),
        migrations.RunPython(migrate_install_status),
        migrations.RemoveField(
            model_name="install",
            name="install_status_old",
        ),
        migrations.AlterField(
            model_name="install",
            name="install_status",
            field=models.TextField(
                choices=[
                    ("Request Received", "Request Received"),
                    ("Pending", "Pending"),
                    ("Blocked", "Blocked"),
                    ("Active", "Active"),
                    ("Inactive", "Inactive"),
                    ("Closed", "Closed"),
                ]
            ),
        ),
    ]

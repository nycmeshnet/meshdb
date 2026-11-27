from django.db import migrations, models

from meshapi.models.devices.oxidized import DEVICE_TYPE_CHOICES


class Migration(migrations.Migration):

    dependencies = [
        ("meshapi", "0014_alter_historicallink_type_alter_link_type"),
    ]

    operations = [
        migrations.AddField(model_name=model_name, name=field_name, field=field)
        for model_name in ("device", "historicalaccesspoint", "historicaldevice", "historicalsector")
        for field_name, field in (
            (
                "ip_address",
                models.GenericIPAddressField(blank=True, null=True, help_text="The IP address"),
            ),
            ("model", models.CharField(blank=True, null=True, help_text="The hardware model of this device")),
            (
                "type",
                models.CharField(
                    blank=True,
                    choices=DEVICE_TYPE_CHOICES,
                    verbose_name="Backup platform",
                    help_text="Oxidized model used for configuration backups, such as routeros or junos.",
                    null=True,
                ),
            ),
        )
    ]

# Generated by Django 4.2.9 on 2024-02-10 18:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0007_alter_install_building_alter_install_member"),
    ]

    operations = [
        migrations.AddField(
            model_name="install",
            name="diy",
            field=models.BooleanField(blank=True, default=None, null=True, verbose_name="Is DIY?"),
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0022_clean_up_fake_intermediate_table"),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE meshapi_install ALTER COLUMN install_number ADD GENERATED BY DEFAULT AS IDENTITY;"
        )
    ]

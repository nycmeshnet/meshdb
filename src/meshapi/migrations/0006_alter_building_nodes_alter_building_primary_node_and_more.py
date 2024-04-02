# Generated by Django 4.2.10 on 2024-04-02 03:16

from django.db import migrations, models
import django.db.models.deletion
import meshapi.models.util.custom_many_to_many


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0005_node_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="building",
            name="nodes",
            field=meshapi.models.util.custom_many_to_many.CustomColumnNameManyToManyField(
                db_from_column_name="building_id",
                db_to_column_name="network_number",
                help_text="All nodes located on the same structure (i.e. a discrete man-made place identified by the same BIN) that this Building is located within.",
                related_name="buildings",
                to="meshapi.node",
            ),
        ),
        migrations.AlterField(
            model_name="building",
            name="primary_node",
            field=models.ForeignKey(
                blank=True,
                db_column="primary_network_number",
                help_text="The primary node for this Building, for cases where it has more than one. This is the node bearing the network number that the building is collquially referred to by volunteers and is usually the first NN held by any equipment on the building. If present, this must also be included in nodes",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="meshapi.node",
            ),
        ),
        migrations.AlterField(
            model_name="device",
            name="node",
            field=models.ForeignKey(
                db_column="network_number",
                help_text="The logical node this Device is located within. The integer value of this field is also the network number, which corresponds to the static IP address and OSPF ID of this device or the DHCP range it receives an address from. This number is also usually found in the device name",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="devices",
                to="meshapi.node",
            ),
        ),
        migrations.AlterField(
            model_name="install",
            name="node",
            field=models.ForeignKey(
                blank=True,
                db_column="network_number",
                help_text="The node this install is associated with, the integer value of this field is also the network number, which corresponds to the static IP address and OSPF ID of the router this install utilizes, the DHCP range it receives an address from, etc.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="installs",
                to="meshapi.node",
            ),
        ),
    ]

# Generated by Django 4.2.9 on 2024-09-06 02:13

import django.db.models.deletion
from django.db import migrations, models


def copy_buildingnode_relation_forward(apps, schema_editor):
    Building = apps.get_model("meshapi", "building")
    BuildingNodeRelation = apps.get_model("meshapi", "TempBuildingNodeRelation")

    for building in Building.objects.all():
        node_ids = set()
        for node in building.nodes.all():
            node_ids.add(node.id)

        for node_id in node_ids:
            new_relation = BuildingNodeRelation(building=building, node_id=node_id)
            new_relation.save()


def copy_buildingnode_relation_reverse(apps, schema_editor):
    BuildingNodeRelation = apps.get_model("meshapi", "TempBuildingNodeRelation")

    for building_node in BuildingNodeRelation.objects.prefetch_related("node").prefetch_related("building").all():
        building_node.building.nodes.add(building_node.node)


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0024_alter_ordering_and_fixup_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="TempBuildingNodeRelation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("building", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="meshapi.building")),
                ("node", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="meshapi.node")),
            ],
        ),
        migrations.RunPython(copy_buildingnode_relation_forward),
        migrations.RemoveField(
            model_name="building",
            name="nodes",
        ),
        migrations.AddField(
            model_name="building",
            name="nodes",
            field=models.ManyToManyField(
                blank=True,
                help_text="All nodes located on the same structure (i.e. a discrete man-made place identified by the same BIN) that this Building is located within.",
                related_name="buildings",
                to="meshapi.node",
            ),
        ),
        migrations.RunPython(copy_buildingnode_relation_reverse),
        migrations.DeleteModel(
            name="TempBuildingNodeRelation",
        ),
    ]

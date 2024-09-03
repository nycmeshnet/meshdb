import uuid
from functools import partial

import django.db.models.deletion
import django.db.models.signals
from django.db import migrations, models


def migrate_integer_id_to_uuid(apps, schema_editor, model_name, int_field_name, uuid_field_name):
    Model = apps.get_model("meshapi", model_name)
    receivers = django.db.models.signals.post_save.receivers
    django.db.models.signals.post_save.receivers = []
    try:
        for obj in Model.objects.all():
            int_val = getattr(obj, int_field_name)
            if int_val:
                setattr(obj, uuid_field_name, uuid.UUID(int=int_val))
                obj.save()
    finally:
        django.db.models.signals.post_save.receivers = receivers


models_with_foreign_keys = {
    "device": ["node"],
    "building": ["primary_node"],
    "install": ["node", "building", "member"],
    "link": ["from_device", "to_device"],
    "los": ["from_building", "to_building"],
    "sector": ["device_ptr"],
    "accesspoint": ["device_ptr"],
    "buildingnode": ["node", "building"],
}


def generate_uuid_proto_foreign_key_operations():
    add_field_operations = []
    run_python_operations = []

    for model_name, foreign_keys in models_with_foreign_keys.items():
        for foreign_key in foreign_keys:
            add_field_operations.append(
                migrations.AddField(
                    model_name=model_name,
                    name=f"{foreign_key}_uuid",
                    field=models.UUIDField(null=True),
                )
            )
            run_python_operations.append(
                migrations.RunPython(
                    partial(
                        migrate_integer_id_to_uuid,
                        model_name=model_name,
                        int_field_name=f"{foreign_key}_id",
                        uuid_field_name=f"{foreign_key}_uuid",
                    )
                )
            )

    return add_field_operations + run_python_operations


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0017_return_to_default_field_names"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="BuildingNode",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                            ),
                        ),
                        (
                            "building",
                            models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="meshapi.building"),
                        ),
                        ("node", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="meshapi.node")),
                    ],
                    options={
                        "db_table": "meshapi_building_nodes",
                        "unique_together": {("building", "node")},
                    },
                ),
                migrations.AlterField(
                    model_name="building",
                    name="nodes",
                    field=models.ManyToManyField(
                        blank=True,
                        help_text="All nodes located on the same structure (i.e. a discrete man-made place identified by the same BIN) that this Building is located within.",
                        related_name="buildings",
                        through="meshapi.BuildingNode",
                        to="meshapi.node",
                    ),
                ),
            ]
        ),
    ] + generate_uuid_proto_foreign_key_operations()

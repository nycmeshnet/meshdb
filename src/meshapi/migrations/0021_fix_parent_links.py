from functools import partial

import django.core.validators
from django.db import migrations, models
from django.db.models import F


def generate_parent_link_repair_operations(model_name, foreign_key_obj):
    return [
        migrations.AddField(
            model_name=model_name,
            name=f"{foreign_key_obj['name']}_new",
            field=foreign_key_obj["pre_field"],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RemoveField(model_name=model_name, name=foreign_key_obj["name"]),
                migrations.RunPython(
                    partial(
                        copy_field,
                        model_name=model_name,
                        from_field_name=f"{foreign_key_obj['name']}_uuid",
                        to_field_name=f"{foreign_key_obj['name']}_new_id",
                    )
                ),
            ]
        ),
        migrations.RemoveField(model_name=model_name, name=f"{foreign_key_obj['name']}_uuid"),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name=model_name, name=f'{foreign_key_obj["name"]}_new'),
            ],
            database_operations=[
                migrations.AlterField(
                    model_name=model_name,
                    name=f"{foreign_key_obj['name']}_new",
                    field=foreign_key_obj["final_field"],
                ),
                migrations.RunSQL(
                    f"ALTER TABLE meshapi_{model_name} RENAME COLUMN {foreign_key_obj['name']}_new_id TO {foreign_key_obj['name']}_id;"
                ),
            ],
        ),
    ]


def copy_field(apps, schema, model_name, from_field_name, to_field_name):
    Model = apps.get_model("meshapi", model_name)
    Model.objects.all().update(**{to_field_name: F(from_field_name)})


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0020_fix_foreign_keys"),
    ]

    operations = generate_parent_link_repair_operations(
        model_name="accesspoint",
        foreign_key_obj={
            "name": "device_ptr",
            "pre_field": models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                serialize=False,
                to="meshapi.device",
                null=True,
            ),
            "final_field": models.OneToOneField(
                auto_created=True,
                parent_link=True,
                on_delete=django.db.models.deletion.CASCADE,
                primary_key=True,
                serialize=False,
                to="meshapi.device",
            ),
        },
    ) + generate_parent_link_repair_operations(
        model_name="sector",
        foreign_key_obj={
            "name": "device_ptr",
            "pre_field": models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                serialize=False,
                to="meshapi.device",
                null=True,
            ),
            "final_field": models.OneToOneField(
                auto_created=True,
                parent_link=True,
                on_delete=django.db.models.deletion.CASCADE,
                primary_key=True,
                serialize=False,
                to="meshapi.device",
            ),
        },
    )

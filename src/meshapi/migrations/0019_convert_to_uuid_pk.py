import uuid
from functools import partial

import django
from django.db import migrations, models
from django.db.models import F


def migrate_integer_id_to_uuid(apps, schema_editor, model_name, int_field_name, uuid_field_name):
    Model = apps.get_model("meshapi", model_name)
    receivers = django.db.models.signals.post_save.receivers
    django.db.models.signals.post_save.receivers = []
    try:
        for obj in Model.objects.all():
            setattr(obj, uuid_field_name, uuid.UUID(int=getattr(obj, int_field_name)))
            obj.save()
    finally:
        django.db.models.signals.post_save.receivers = receivers


def copy_field(apps, schema, model_name, from_field_name, to_field_name):
    Model = apps.get_model("meshapi", model_name)
    Model.objects.all().update(**{to_field_name: F(from_field_name)})


model_pk_field_names = {
    "device": "id",
    "building": "id",
    "install": "install_number",
    "link": "id",
    "los": "id",
    "member": "id",
    "node": "network_number",
}


def generate_uuid_pk_migrations():
    preprocess_operations = []
    run_python_operations = []
    postprocess_operations = []
    cleanup_operations = []

    for model_name, primary_key in model_pk_field_names.items():
        preprocess_operations.append(
            migrations.AddField(
                model_name=model_name,
                name="id_new",
                field=models.UUIDField(null=True, editable=False, serialize=False),
            ),
        )

        run_python_operations.append(
            migrations.RunPython(
                partial(
                    migrate_integer_id_to_uuid,
                    model_name=model_name,
                    int_field_name=f"{primary_key}",
                    uuid_field_name="id_new",
                )
            ),
        )

        if primary_key != "id":
            preprocess_operations.append(
                migrations.AddField(
                    model_name=model_name,
                    name=f"{primary_key}_new",
                    field=models.IntegerField(unique=True, null=True),
                ),
            )
            run_python_operations.append(
                migrations.RunPython(
                    partial(
                        copy_field,
                        model_name=model_name,
                        from_field_name=f"{primary_key}",
                        to_field_name=f"{primary_key}_new",
                    ),
                ),
            )
            postprocess_operations.append(
                migrations.AlterField(
                    model_name=model_name,
                    name=f"{primary_key}_new",
                    field=models.IntegerField(unique=True, null=False),
                )
            )
            cleanup_operations.append(
                migrations.RenameField(model_name=model_name, old_name=f"{primary_key}_new", new_name=primary_key)
            )

        postprocess_operations.append(
            migrations.RemoveField(
                model_name=model_name,
                name=f"{primary_key}",
            ),
        )

        postprocess_operations.append(
            migrations.AlterField(
                model_name=model_name,
                name="id_new",
                field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
            ),
        )
        cleanup_operations.append(migrations.RenameField(model_name=model_name, old_name="id_new", new_name="id"))

    return preprocess_operations + run_python_operations + postprocess_operations + cleanup_operations


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0018_populate_uuid_proto_foreign_keys"),
    ]

    operations = generate_uuid_pk_migrations() + [
        migrations.AlterField(
            model_name="node",
            name="network_number",
            field=models.IntegerField(
                unique=True,
                validators=[django.core.validators.MaxValueValidator(8192)],
                null=False,
            ),
        ),
    ]

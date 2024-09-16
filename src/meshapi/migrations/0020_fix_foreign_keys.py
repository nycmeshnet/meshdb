from functools import partial

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def copy_field(apps, schema, model_name, from_field_name, to_field_name):
    Model = apps.get_model("meshapi", model_name)
    Model.objects.all().update(**{to_field_name: F(from_field_name)})


models_with_foreign_keys = {
    "device": [
        {
            "name": "node",
            "pre_field": models.ForeignKey(
                help_text="The logical node this Device is located within. The integer value of this field is also the network number, which corresponds to the static IP address and OSPF ID of this device or the DHCP range it receives an address from. This number is also usually found in the device name",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="devices",
                to="meshapi.node",
                null=True,
            ),
            "final_field": models.ForeignKey(
                help_text="The logical node this Device is located within. The integer value of this field is also the network number, which corresponds to the static IP address and OSPF ID of this device or the DHCP range it receives an address from. This number is also usually found in the device name",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="devices",
                to="meshapi.node",
            ),
        }
    ],
    "building": [
        {
            "name": "primary_node",
            "pre_field": models.ForeignKey(
                blank=True,
                help_text="The primary node for this Building, for cases where it has more than one. This is the node bearing the network number that the building is collquially referred to by volunteers and is usually the first NN held by any equipment on the building. If present, this must also be included in nodes",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="meshapi.node",
            ),
            "final_field": models.ForeignKey(
                blank=True,
                help_text="The primary node for this Building, for cases where it has more than one. This is the node bearing the network number that the building is collquially referred to by volunteers and is usually the first NN held by any equipment on the building. If present, this must also be included in nodes",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="meshapi.node",
            ),
        }
    ],
    "install": [
        {
            "name": "node",
            "pre_field": models.ForeignKey(
                blank=True,
                help_text="The node this install is associated with, the integer value of this field is also the network number, which corresponds to the static IP address and OSPF ID of the router this install utilizes, the DHCP range it receives an address from, etc.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="installs",
                to="meshapi.node",
            ),
            "final_field": models.ForeignKey(
                blank=True,
                help_text="The node this install is associated with, the integer value of this field is also the network number, which corresponds to the static IP address and OSPF ID of the router this install utilizes, the DHCP range it receives an address from, etc.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="installs",
                to="meshapi.node",
            ),
        },
        {
            "name": "building",
            "pre_field": models.ForeignKey(
                help_text="The building where the install is located. In the case of a structure with multiple buildings, this will be the building whose address makes sense for this install's unit.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="installs",
                to="meshapi.building",
                null=True,
            ),
            "final_field": models.ForeignKey(
                help_text="The building where the install is located. In the case of a structure with multiple buildings, this will be the building whose address makes sense for this install's unit.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="installs",
                to="meshapi.building",
            ),
        },
        {
            "name": "member",
            "pre_field": models.ForeignKey(
                help_text="The member this install is associated with",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="installs",
                to="meshapi.member",
            ),
            "final_field": models.ForeignKey(
                help_text="The member this install is associated with",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="installs",
                to="meshapi.member",
            ),
        },
    ],
    "link": [
        {
            "name": "from_device",
            "pre_field": models.ForeignKey(
                help_text="The device on one side of this network link, from/to are not meaningful except to disambiguate",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="links_from",
                to="meshapi.device",
                null=True,
            ),
            "final_field": models.ForeignKey(
                help_text="The device on one side of this network link, from/to are not meaningful except to disambiguate",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="links_from",
                to="meshapi.device",
            ),
        },
        {
            "name": "to_device",
            "pre_field": models.ForeignKey(
                help_text="The device on one side of this network link, from/to are not meaningful except to disambiguate",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="links_to",
                to="meshapi.device",
                null=True,
            ),
            "final_field": models.ForeignKey(
                help_text="The device on one side of this network link, from/to are not meaningful except to disambiguate",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="links_to",
                to="meshapi.device",
            ),
        },
    ],
    "los": [
        {
            "name": "from_building",
            "pre_field": models.ForeignKey(
                help_text="The building on one side of this LOS, from/to are not meaningful except to disambiguate",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="los_from",
                to="meshapi.building",
                null=True,
            ),
            "final_field": models.ForeignKey(
                help_text="The building on one side of this LOS, from/to are not meaningful except to disambiguate",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="los_from",
                to="meshapi.building",
            ),
        },
        {
            "name": "to_building",
            "pre_field": models.ForeignKey(
                help_text="The building on one side of this LOS, from/to are not meaningful except to disambiguate",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="los_to",
                to="meshapi.building",
                null=True,
            ),
            "final_field": models.ForeignKey(
                help_text="The building on one side of this LOS, from/to are not meaningful except to disambiguate",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="los_to",
                to="meshapi.building",
            ),
        },
    ],
    "buildingnode": [
        {
            "name": "node",
            "pre_field": models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="meshapi.node",
                null=True,
            ),
            "final_field": models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="meshapi.node",
            ),
        },
        {
            "name": "building",
            "pre_field": models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="meshapi.building",
                null=True,
            ),
            "final_field": models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="meshapi.building",
            ),
        },
    ],
}


def generate_uuid_fk_migrations():
    preprocess_operations = []
    run_python_operations = []
    postprocess_operations = []

    for model_name, foreign_keys in models_with_foreign_keys.items():
        for foreign_key_obj in foreign_keys:
            preprocess_operations.append(
                migrations.RemoveField(model_name=model_name, name=foreign_key_obj["name"]),
            )
            preprocess_operations.append(
                migrations.AddField(
                    model_name=model_name, name=foreign_key_obj["name"], field=foreign_key_obj["pre_field"]
                ),
            )

            run_python_operations.append(
                migrations.RunPython(
                    partial(
                        copy_field,
                        model_name=model_name,
                        from_field_name=f"{foreign_key_obj['name']}_uuid",
                        to_field_name=f"{foreign_key_obj['name']}_id",
                    )
                ),
            )

            if "final_field" in foreign_key_obj:
                postprocess_operations.append(
                    migrations.RemoveField(model_name=model_name, name=f"{foreign_key_obj['name']}_uuid"),
                )
                postprocess_operations.append(
                    migrations.AlterField(
                        model_name=model_name,
                        name=foreign_key_obj["name"],
                        field=foreign_key_obj["final_field"],
                    ),
                )

    return preprocess_operations + run_python_operations + postprocess_operations


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0019_convert_to_uuid_pk"),
    ]

    operations = generate_uuid_fk_migrations()

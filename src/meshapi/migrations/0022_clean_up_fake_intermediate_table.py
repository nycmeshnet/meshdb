from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0021_fix_parent_links"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="building",
                    name="nodes",
                    field=models.ManyToManyField(
                        blank=True,
                        help_text="All nodes located on the same structure (i.e. a discrete man-made place identified by the same BIN) that this Building is located within.",
                        related_name="buildings",
                        to="meshapi.node",
                    ),
                ),
                migrations.DeleteModel(
                    name="BuildingNode",
                ),
            ]
        )
    ]

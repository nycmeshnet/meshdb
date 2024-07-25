from django.db import models

from meshapi.models import Building


class LOS(models.Model):
    """
    A LOS represents a pair of MeshDB Building objects which are able to see each other. This indicates
    they are potential candidates for linking together. In fact, this table is currently primarily useful
    for storing human-entered "potential" links.

    This is needed because unlike the legacy spreadsheet, MeshDB's Link table stores connections
    between Device objects, not between install numbers. This means among other things that in order
    to show a potential link on the map, we'd need to assign NNs to those buildings (very gross). Instead,
    with this table, we can represent potential links between any pair of street addresses (MeshDB
    Buildings), no need to create any other DB objects.
    """

    class Meta:
        verbose_name = "LOS"
        verbose_name_plural = "LOSes"

    class LOSSource(models.TextChoices):
        HUMAN_ANNOTATED = "Human Annotated"
        EXISTING_LINK = "Existing Link"

    from_building = models.ForeignKey(
        Building,
        on_delete=models.PROTECT,
        related_name="los_from",
        help_text="The building on one side of this LOS, from/to are not meaningful except to disambiguate",
    )
    to_building = models.ForeignKey(
        Building,
        on_delete=models.PROTECT,
        related_name="los_to",
        help_text="The building on one side of this LOS, from/to are not meaningful except to disambiguate",
    )

    analysis_date = models.DateField(
        help_text="The date we conducted the analysis that concluded this LOS exists. "
        "Important since new buildings might have been built which block the LOS after this date",
    )

    source = models.CharField(
        choices=LOSSource.choices, help_text="The source of information that tells us this LOS exists"
    )

    notes = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="A free-form text description of this LOS, to track any additional information.",
    )

    def __str__(self) -> str:
        def building_to_number(building: Building) -> str:
            if building.primary_node:
                return f"NN{building.primary_node.network_number}"

            if building.installs:
                return f"#{building.installs.first().install_number}"

            return f"MeshDB building ID {building.id}"

        return f"{building_to_number(self.from_building)} → {building_to_number(self.to_building)}"

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django_jsonform.models.fields import ArrayField as JSONFormArrayField

from meshdb.utils.spreadsheet_import.building.constants import AddressTruthSource

from .node import Node
from .util.custom_many_to_many import CustomColumnNameManyToManyField


class Building(models.Model):
    """
    A building represents a single discrete place represented by street address. This may be located
    within a larger structure with multiple street addresses.

    If located within NYC, this will usually have a BIN number. However, this BIN number is not
    necessarily unique. In the case of a structure with multiple street addresses, we create a
    "Building" object for each address, but these "Building" objects will all share a BIN.
    """

    bin = models.IntegerField(
        blank=True,
        null=True,
        help_text="NYC DOB Identifier for the structure containing this building",
        validators=[MinValueValidator(0)],
    )

    street_address = models.CharField(
        blank=True, null=True, help_text="Line 1 only of the address of this building: i.e. <house num> <street>"
    )
    city = models.CharField(
        blank=True,
        null=True,
        help_text="The name of the borough this building is in for buildings within NYC, "
        '"New York" for Manhattan to match street addresses. The actual city name for anything outside NYC',
    )
    state = models.CharField(
        blank=True,
        null=True,
        help_text='The 2 letter abreviation of the US State this building is contained within, e.g. "NY" or "NJ"',
    )
    zip_code = models.CharField(
        blank=True, null=True, help_text="The five digit ZIP code this building is contained within"
    )

    address_truth_sources = ArrayField(
        models.CharField(
            choices=list((src.value, src.name) for src in AddressTruthSource),
        ),
        help_text="A list of strings that answers the question: How was the content of"
        "the street address, city, state, and ZIP fields determined? This is useful in understanding the level of validation "
        "applied to spreadsheet imported data. Possible values are: "
        f"{', '.join(src.value for src in AddressTruthSource)}. Check the import script for details",
    )

    latitude = models.FloatField(help_text="Building latitude in decimal degrees")
    longitude = models.FloatField(help_text="Building longitude in decimal degrees")
    altitude = models.FloatField(
        blank=True, null=True, help_text='Building rooftop altitude in "absolute" meters above mean sea level'
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="A free-form text description of this building, to track any additional information. "
        "For Buidings imported from the spreadsheet, this starts with a formatted block of information about the import process"
        "and original spreadsheet data. However this structure can be changed by admins at any time and should not be relied on"
        "by automated systems. ",
    )
    panoramas = JSONFormArrayField(
        models.URLField(),
        null=True,
        blank=True,
        default=list,
        help_text="Panoramas taken from the roof of this Building",
    )

    primary_node = models.ForeignKey(
        Node,
        on_delete=models.PROTECT,
        related_name="+",  # Don't allow reverse access, since this will be included via nodes below
        db_column="primary_network_number",
        help_text="The primary node for this Building, for cases where it has more than one. This is the node "
        "bearing the network number that the building is collquially referred to by volunteers and is "
        "usually the first NN held by any equipment on the building. If present, this must also be included in nodes",
        blank=True,
        null=True,
    )
    nodes = CustomColumnNameManyToManyField(
        Node,
        db_from_column_name="building_id",
        db_to_column_name="network_number",
        help_text="All nodes located on the same structure (i.e. a discrete man-made place identified by the same BIN) "
        "that this Building is located within.",
        related_name="buildings",
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Ensure primary_node is always contained in nodes
        if self.primary_node and self.primary_node not in self.nodes.all():
            self.nodes.add(self.primary_node)

    def __str__(self):
        if self.street_address:
            addr_str = str(self.street_address)
            if self.city:
                addr_str += f", {self.city}"
            if self.state:
                addr_str += f", {self.state}"
            return addr_str
        if self.bin:
            return f"BIN {self.bin}"
        return f"MeshDB Building ID {self.id}"

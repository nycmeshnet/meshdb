import uuid
from enum import Enum
from typing import Any

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import ManyToManyField
from django_jsonform.models.fields import ArrayField as JSONFormArrayField
from simple_history.models import HistoricalRecords

from .node import Node


class AddressTruthSource(Enum):
    OSMNominatim = "OSMNominatim"
    OSMNominatimZIPOnly = "OSMNominatimZIPOnly"
    NYCPlanningLabs = "NYCPlanningLabs"
    PeliasStringParsing = "PeliasStringParsing"
    ReverseGeocodeFromCoordinates = "ReverseGeocodeFromCoordinates"
    HumanEntry = "HumanEntry"


class Building(models.Model):
    """
    A building represents a single discrete place represented by street address. This may be located
    within a larger structure with multiple street addresses.

    If located within NYC, this will usually have a BIN number. However, this BIN number is not
    necessarily unique. In the case of a structure with multiple street addresses, we create a
    "Building" object for each address, but these "Building" objects will all share a BIN.
    """

    history = HistoricalRecords(m2m_fields=["nodes"])

    class Meta:
        indexes = [
            models.Index(fields=["bin"]),
            models.Index(fields=["street_address"]),
            models.Index(fields=["zip_code"]),
        ]
        ordering = ["id"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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
        help_text="A list of strings that answers the question: How was the content of "
        "the street address, city, state, and ZIP fields determined? This is useful in "
        "understanding the level of validation applied to spreadsheet imported data. Possible values are: "
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
        "For Buidings imported from the spreadsheet, this starts with a formatted block of information about "
        "the import process and original spreadsheet data. However this structure can be changed by admins at "
        "any time and should not be relied on by automated systems. ",
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
        help_text="The primary node for this Building, for cases where it has more than one. This is the node "
        "bearing the network number that the building is collquially referred to by volunteers and is "
        "usually the first NN held by any equipment on the building. If present, this must also be included in nodes",
        blank=True,
        null=True,
    )
    nodes = ManyToManyField(
        Node,
        blank=True,
        help_text="All nodes located on the same structure (i.e. a discrete man-made place identified by the same BIN) "
        "that this Building is located within.",
        related_name="buildings",
    )

    def save(self, *args: Any, **kwargs: Any) -> None:
        super().save(*args, **kwargs)

        # Ensure primary_node is always contained in nodes
        if self.primary_node and self.primary_node not in self.nodes.all():
            self.nodes.add(self.primary_node)

    @property
    def one_line_complete_address(self) -> str:
        addr_components = []
        if self.street_address:
            addr_components.append(self.street_address)
        if self.city or self.state:
            city_state = []
            if self.city:
                city_state.append(self.city)
            if self.state:
                city_state.append(self.state)
            addr_components.append(" ".join(city_state))
        if self.zip_code:
            addr_components.append(self.zip_code)

        return ", ".join(addr_components)

    def __str__(self) -> str:
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

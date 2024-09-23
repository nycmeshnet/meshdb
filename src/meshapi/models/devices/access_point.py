from django.db import models
from simple_history.models import HistoricalRecords

from .device import Device


class AccessPoint(Device):
    history = HistoricalRecords()

    latitude = models.FloatField(
        help_text="Approximate AP latitude in decimal degrees (this will match the attached "
        "Node object in most cases, but has been manually moved around in some cases to "
        "more accurately reflect the device location)"
    )
    longitude = models.FloatField(
        help_text="Approximate AP longitude in decimal degrees (this will match the attached "
        "Node object in most cases, but has been manually moved around in some cases to "
        "more accurately reflect the device location)"
    )
    altitude = models.FloatField(
        blank=True,
        null=True,
        help_text='Approximate AP altitude in "absolute" meters above mean sea level (this '
        "will match the attached Node object in most cases, but has been manually moved around in "
        "some cases to more accurately reflect the device location)",
    )

    def __str__(self) -> str:
        if self.name:
            return self.name
        return f"MeshDB AP ID {self.id}"

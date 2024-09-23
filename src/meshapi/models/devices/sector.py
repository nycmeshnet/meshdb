from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from .device import Device


class Sector(Device):
    history = HistoricalRecords()

    radius = models.FloatField(
        help_text="The radius to display this sector on the map (in km)",
        validators=[MinValueValidator(0)],
    )
    azimuth = models.IntegerField(
        help_text="The compass heading that this sector is pointed towards",
        validators=[
            MinValueValidator(0),
            MaxValueValidator(360),
        ],
    )
    width = models.IntegerField(
        help_text="The approximate width of the beam this sector produces",
        validators=[
            MinValueValidator(0),
            MaxValueValidator(360),
        ],
    )

    def __str__(self) -> str:
        if self.name:
            return self.name
        return f"MeshDB Sector ID {self.id}"

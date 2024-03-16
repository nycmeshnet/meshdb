from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .device import Device


class Sector(Device):
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

    def __str__(self):
        if self.ssid:
            return self.ssid
        return f"MeshDB Sector ID {self.id}"

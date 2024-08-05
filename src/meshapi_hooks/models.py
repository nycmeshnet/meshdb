from django.db import models
from django import forms

# drf-hooks looks in this file for hook objects, but it feels weird to inline
# it here, so we import it instead
from .hooks import CelerySerializerHook
class ContactPreference(models.TextChoices):
    """Defines the available contact preference options."""
    PHONE = 'phone', ('Phone')
    EMAIL = 'email', ('Email')

class Member(models.Model):
    """Represents a member in the system."""

    # Existing member fields (replace with your actual fields)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    # ... other fields

    contact_preference = models.CharField(
        max_length=5,
        choices=ContactPreference.choices,
        blank=True,  # Allow null values for existing members
        default=None,  # Avoid setting a default for existing members
        help_text=("How would you like us to contact you?"),
    )

    # ... other member-related methods (if applicable)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

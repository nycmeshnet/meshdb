import uuid
from typing import Any, List

from django.db import models
from django.db.models.fields import EmailField
from django_jsonform.models.fields import ArrayField as JSONFormArrayField
from simple_history.models import HistoricalRecords

from meshapi.validation import normalize_phone_number, validate_multi_phone_number_field, validate_phone_number_field


class Member(models.Model):
    history = HistoricalRecords()
    payment_preference_choices = (
        (None, "None"),
        ("cash", "Cash"),
        ("stripe", "Stripe"),
    )

    class Meta:
        ordering = ["id"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(help_text='Member full name in the format: "First Last"')
    primary_email_address = models.EmailField(
        blank=True, null=True, help_text="Primary email address used to contact the member"
    )
    stripe_email_address = models.EmailField(
        null=True,
        blank=True,
        default=None,
        help_text="Email address used by the member to donate via Stripe, if different to their primary email",
    )
    additional_email_addresses = JSONFormArrayField(
        EmailField(),
        null=True,
        blank=True,
        default=list,
        help_text="Any additional email addresses associated with this member",
    )
    phone_number = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text="A primary contact phone number for this member",
        validators=[validate_phone_number_field],
    )
    additional_phone_numbers = JSONFormArrayField(
        models.CharField(),
        default=list,
        null=True,
        blank=True,
        help_text="Any additional phone numbers used by this member",
        validators=[validate_multi_phone_number_field],
    )
    slack_handle = models.CharField(default=None, blank=True, null=True, help_text="The member's slack handle")
    notes = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="A free-form text description of how to contact this member, to track any additional information. "
        "For Members imported from the spreadsheet, this starts with a formatted block of information about the "
        "import process and original spreadsheet data. However this structure can be changed by admins at any "
        "time and should not be relied on by automated systems. ",
    )
    payment_preference = models.CharField(default=None, choices=payment_preference_choices, blank=True, null=True)

    def __str__(self) -> str:
        if self.name:
            return self.name
        return f"MeshDB Member ID {self.id}"

    @property
    def all_email_addresses(self) -> List[str]:
        all_emails = []
        if self.primary_email_address and self.primary_email_address not in all_emails:
            all_emails.append(self.primary_email_address)

        if self.stripe_email_address and self.stripe_email_address not in all_emails:
            all_emails.append(self.stripe_email_address)

        if self.additional_email_addresses:
            for email in self.additional_email_addresses:
                if email not in all_emails:
                    all_emails.append(email)

        return all_emails

    @property
    def all_phone_numbers(self) -> List[str]:
        all_phone_numbers = []
        if self.phone_number and self.phone_number not in all_phone_numbers:
            all_phone_numbers.append(self.phone_number)

        if self.additional_phone_numbers:
            for phone_number in self.additional_phone_numbers:
                if phone_number not in all_phone_numbers:
                    all_phone_numbers.append(phone_number)

        return all_phone_numbers

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.phone_number:
            self.phone_number = normalize_phone_number(self.phone_number)
        if self.additional_phone_numbers:
            self.additional_phone_numbers = [
                normalize_phone_number(num) for num in self.additional_phone_numbers if num
            ]
        super().save(*args, **kwargs)

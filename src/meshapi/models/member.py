from typing import List

from django.db import models
from django.db.models.fields import EmailField
from django_jsonform.models.fields import ArrayField as JSONFormArrayField

from meshapi.validation import validate_phone_number_field


class Member(models.Model):
    name = models.CharField(help_text='Member full name in the format: "First Last"')
    primary_email_address = models.EmailField(null=True, help_text="Primary email address used to contact the member")
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
        help_text="A contact phone number for this member",
        validators=[validate_phone_number_field],
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

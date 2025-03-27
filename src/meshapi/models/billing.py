import uuid

from django.db import models
from simple_history.models import HistoricalRecords


class InstallFeeBillingDatum(models.Model):
    """
    For some installs, another organization is responsible for paying install fees, rather than the
    resident of the apartment we have installed. This object tracks additional data relevant to that
    situation, such as when/if the invoice has been sent, what invoice a given install was
    included on, etc.
    """

    class Meta:
        verbose_name = "Install Fee Billing Datum"
        verbose_name_plural = "Install Fee Billing Data"

    history = HistoricalRecords()

    class BillingStatus(models.TextChoices):
        TO_BE_BILLED = "ToBeBilled", "To Be Billed"
        BILLED = "Billed", "Billed"
        NOT_BILLING_DUPLICATE = "NotBillingDuplicate", "Not Billing - Duplicate"
        NOT_BILLING_OTHER = "NotBillingOther", "Not Billing - Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    install = models.OneToOneField(
        "Install",
        related_name="install_fee_billing_datum",
        on_delete=models.PROTECT,
        help_text="Which Install object does this billing data refer to",
    )

    status = models.CharField(
        choices=BillingStatus.choices,
        help_text="The billing status of the associated install",
        default=BillingStatus.TO_BE_BILLED,
    )

    billing_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The date that the associated install was billed to the responsible organization",
    )

    invoice_number = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text="The invoice number that the associated install was billed via",
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="A free-form text description, to track any additional information.",
    )

    def __str__(self) -> str:
        return f"Billing Datum for {self.install}"

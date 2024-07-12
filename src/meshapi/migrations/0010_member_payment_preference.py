from django.db import migrations, models

class PaymentPreference(models.TextChoices):
    CASH = "cash", "Cash"
    STRIPE = "stripe", "Stripe"
    NONE = None, "None"

class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0009_member_additional_phone_numbers_alter_member_phone_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="member",
            name="payment_preference",
            field=models.CharField(
                max_length=6,
                choices=PaymentPreference.choices,
                default=PaymentPreference.NONE,
                help_text="Preferred payment method for this member",
            ),
        ),
    ]
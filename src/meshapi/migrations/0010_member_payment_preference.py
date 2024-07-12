from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0009_member_additional_phone_numbers_alter_member_phone_number"),

    operations = [
        migrations.AddField(
            model_name="member",
            name="payment_preference",
            field=models.CharField(
                choices=[
                    ("cash", "Cash"),
                    ("stripe", "Stripe"),
                    (None, "None"),
                ],
                default=None,
                help_text="Preferred payment method for this member",
                null=True,
                blank=True,
            ),
        ),
    ]
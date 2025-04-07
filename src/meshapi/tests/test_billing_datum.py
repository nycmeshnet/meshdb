import datetime
import json

from django.contrib.auth.models import User
from django.test import TestCase

from ..models import Building, Install, InstallFeeBillingDatum, Member
from .sample_data import sample_building, sample_install, sample_member


class TestInstallFeeBillingDatum(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.client.login(username="admin", password="admin_password")

        self.building_1 = Building(**sample_building)
        self.building_1.save()

        self.member = Member(**sample_member)
        self.member.save()

        self.install = Install(
            **sample_install,
            install_number=123,
            member=self.member,
            building=self.building_1,
        )
        self.install.save()

    def test_new_billing_datum(self):
        response = self.client.post(
            "/api/v1/billing/install-fee-data/",
            {
                "install": {"id": str(self.install.id)},
                "status": "ToBeBilled",
                "billing_date": "2025-01-01",
                "invoice_number": "12345",
                "notes": "foo bar\nbaz",
            },
            content_type="application/json",
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_new_billing_datum_default_status(self):
        response = self.client.post(
            "/api/v1/billing/install-fee-data/",
            {
                "install": {"install_number": 123},
                "billing_date": "2025-01-01",
                "invoice_number": "12345",
                "notes": "foo bar\nbaz",
            },
            content_type="application/json",
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        self.assertEqual(
            InstallFeeBillingDatum.BillingStatus.TO_BE_BILLED, InstallFeeBillingDatum.objects.first().status
        )

    def test_broken_billing_datum(self):
        response = self.client.post(
            "/api/v1/billing/install-fee-data/",
            {
                # install is required and missing
                "billing_date": "2025-01-01",
                "invoice_number": "12345",
                "notes": "foo bar\nbaz",
            },
            content_type="application/json",
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_get_billing_datum(self):
        billing_datum = InstallFeeBillingDatum(
            install=self.install,
            status=InstallFeeBillingDatum.BillingStatus.TO_BE_BILLED,
            billing_date=datetime.date(2025, 1, 1),
            invoice_number="12345",
        )
        billing_datum.save()

        response = self.client.get(f"/api/v1/billing/install-fee-data/{billing_datum.id}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["status"], "ToBeBilled")
        self.assertEqual(response_obj["install"]["install_number"], self.install.install_number)
        self.assertEqual(response_obj["install"]["id"], str(self.install.id))
        self.assertEqual(response_obj["invoice_number"], "12345")

    def test_modify_status(self):
        billing_datum = InstallFeeBillingDatum(
            install=self.install,
            status=InstallFeeBillingDatum.BillingStatus.TO_BE_BILLED,
            billing_date=datetime.date(2025, 1, 1),
            invoice_number="12345",
        )
        billing_datum.save()
        response = self.client.patch(
            f"/api/v1/billing/install-fee-data/{billing_datum.id}/",
            {"status": "Billed"},
            content_type="application/json",
        )

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        billing_datum.refresh_from_db()
        self.assertEqual(InstallFeeBillingDatum.BillingStatus.BILLED, billing_datum.status)

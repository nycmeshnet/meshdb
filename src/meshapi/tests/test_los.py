import datetime
import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import LOS, Building
from .sample_data import sample_building


class TestLOS(TestCase):
    c = Client()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")

        self.building1 = Building(**sample_building)
        self.building1.save()

        self.building2 = Building(**sample_building)
        self.building2.save()

        self.today = datetime.date.today()

        self.LOS = LOS(
            from_building=self.building1,
            to_building=self.building2,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=self.today,
        )
        self.LOS.save()

    def test_new_LOS(self):
        response = self.c.post(
            "/api/v1/loses/",
            {
                "from_building": self.building1.id,
                "to_building": self.building2.id,
                "source": "Human Annotated",
                "analysis_date": "2024-07-24",
            },
        )
        code = 201
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_broken_LOS(self):
        response = self.c.post(
            "/api/v1/loses/",
            {
                "from_building": "",
                "to_building": self.building2.id,
                "source": "Human Annotated",
                "analysis_date": "2024-07-24",
            },
        )
        code = 400
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

    def test_get_LOS(self):
        los = LOS(
            from_building=self.building1,
            to_building=self.building2,
            source=LOS.LOSSource.HUMAN_ANNOTATED,
            analysis_date=self.today,
        )
        los.save()

        response = self.c.get(f"/api/v1/loses/{los.id}/")

        code = 200
        self.assertEqual(
            code,
            response.status_code,
            f"status code incorrect. Should be {code}, but got {response.status_code}",
        )

        response_obj = json.loads(response.content)
        self.assertEqual(response_obj["source"], "Human Annotated")
        self.assertEqual(response_obj["from_building"], self.building1.id)
        self.assertEqual(response_obj["to_building"], self.building2.id)
        self.assertEqual(response_obj["analysis_date"], self.today.isoformat())


# TODO: Write tests for the more advanced features we wrote here

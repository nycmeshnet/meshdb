import datetime
import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from ..models import LOS, Building, Install, Member, Node
from .sample_data import sample_building, sample_install, sample_member, sample_node


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
                "from_building": {"id": str(self.building1.id)},
                "to_building": {"id": str(self.building2.id)},
                "source": "Human Annotated",
                "analysis_date": "2024-07-24",
            },
            content_type="application/json",
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
                "from_building": {"id": ""},
                "to_building": {"id": str(self.building2.id)},
                "source": "Human Annotated",
                "analysis_date": "2024-07-24",
            },
            content_type="application/json",
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
        self.assertEqual(response_obj["from_building"]["id"], str(self.building1.id))
        self.assertEqual(response_obj["to_building"]["id"], str(self.building2.id))
        self.assertEqual(response_obj["analysis_date"], self.today.isoformat())

    def test_string_name(self):
        self.assertEqual(
            str(self.LOS), f"MeshDB building ID {self.building1.id} → MeshDB building ID {self.building2.id}"
        )

        test_node = Node(**sample_node)
        test_node.network_number = 123
        test_node.save()

        self.building1.primary_node = test_node
        self.building1.save()

        test_member = Member(**sample_member)
        test_member.save()

        sample_install_minimal = sample_install.copy()
        test_install = Install(**sample_install_minimal)
        test_install.install_number = 12345
        test_install.building = self.building2
        test_install.member = test_member
        test_install.save()

        self.assertEqual(str(self.LOS), "NN123 → #12345")

from django.test import TestCase

from meshapi.models import Building


class TestBuilding(TestCase):
    def test_building_address_single_line_str(self):
        full_address_building = Building(
            street_address="123 Chom Street",
            city="Brooklyn",
            state="NY",
            zip_code="12345",
            latitude=0,
            longitude=0,
        )
        self.assertEqual(full_address_building.one_line_complete_address, "123 Chom Street, Brooklyn NY, 12345")

        limited_address_building = Building(
            street_address="123 Chom Street",
            latitude=0,
            longitude=0,
        )
        self.assertEqual(limited_address_building.one_line_complete_address, "123 Chom Street")

import requests_mock
from django.contrib.auth.models import User
from django.test import TestCase

from meshapi.tests.sample_geocode_response import (
    INVALID_ADDRESS_GEOCODE_RESPONSE,
    VALID_ADDRESS_GEOCODE_RESPONSE,
    VALID_BUILDING_HEIGHT_RESPONSE,
)
from meshapi.validation import BUILDING_FOOTPRINTS_API, NYC_GEOSEARCH_API


class TestGeocodeProxy(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user", password="password", email="user@example.com")
        self.client.force_login(self.user)

    def test_geocode_unauth(self):
        self.client.logout()
        response = self.client.get("/api/v1/geography/nyc-geocode/v2/search?street_addr=blah")
        self.assertEqual(
            403,
            response.status_code,
            f"status code incorrect, should be 403, but got {response.status_code}",
        )

    def test_geocode_missing_params(self):
        response = self.client.get("/api/v1/geography/nyc-geocode/v2/search?street_addr=blah")
        self.assertEqual(
            400,
            response.status_code,
            f"status code incorrect, should be 400, but got {response.status_code}",
        )

    @requests_mock.Mocker(real_http=True)
    def test_geocode_good_addr(self, request_mocker):
        request_mocker.get(NYC_GEOSEARCH_API, json=VALID_ADDRESS_GEOCODE_RESPONSE)
        request_mocker.get(BUILDING_FOOTPRINTS_API, json=VALID_BUILDING_HEIGHT_RESPONSE)

        response = self.client.get(
            "/api/v1/geography/nyc-geocode/v2/search?street_address=151+Broome+St&city=New+York&state=NY&zip=10002"
        )
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(), {"BIN": "1077609", "altitude": 12.4, "latitude": 40.716245, "longitude": -73.98492}
        )

    @requests_mock.Mocker()
    def test_geocode_bad_addr(self, request_mocker):
        request_mocker.get(NYC_GEOSEARCH_API, json=INVALID_ADDRESS_GEOCODE_RESPONSE)

        response = self.client.get(
            "/api/v1/geography/nyc-geocode/v2/search?street_address=12341+Whackadoole+Ave&city=New+York&state=NY&zip=10002"
        )
        self.assertEqual(
            404,
            response.status_code,
            f"status code incorrect, should be 404, but got {response.status_code}",
        )

    @requests_mock.Mocker()
    def test_geocode_non_nyc_addr(self, request_mocker):
        response = self.client.get(
            "/api/v1/geography/nyc-geocode/v2/search?street_address=12341+Whackadoole+Ave&city=Bevery+Hills&state=CA&zip=90210"
        )
        self.assertEqual(
            404,
            response.status_code,
            f"status code incorrect, should be 404, but got {response.status_code}",
        )

    @requests_mock.Mocker()
    def test_geocode_city_api_down(self, request_mocker):
        request_mocker.get(NYC_GEOSEARCH_API, status_code=502)

        response = self.client.get(
            "/api/v1/geography/nyc-geocode/v2/search?street_address=151+Broome+St&city=New+York&state=NY&zip=10002"
        )
        self.assertEqual(
            500,
            response.status_code,
            f"status code incorrect, should be 500, but got {response.status_code}",
        )

    @requests_mock.Mocker(real_http=True)
    def test_geocode_city_height_api_down(self, request_mocker):
        request_mocker.get(NYC_GEOSEARCH_API, json=VALID_ADDRESS_GEOCODE_RESPONSE)
        request_mocker.get(BUILDING_FOOTPRINTS_API, status_code=502)

        response = self.client.get(
            "/api/v1/geography/nyc-geocode/v2/search?street_address=151+Broome+St&city=New+York&state=NY&zip=10002"
        )
        self.assertEqual(
            200,
            response.status_code,
            f"status code incorrect, should be 200, but got {response.status_code}",
        )
        self.assertEqual(
            response.json(), {"BIN": "1077609", "altitude": None, "latitude": 40.716245, "longitude": -73.98492}
        )

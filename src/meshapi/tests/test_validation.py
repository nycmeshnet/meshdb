import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from meshapi.exceptions import AddressAPIError, AddressError
from meshapi.tests.sample_data import sample_address_response, sample_osm_address_response
from meshapi.util.constants import INVALID_ALTITUDE
from meshapi.validation import NYCAddressInfo, AddressInfo, OSMAddressInfo


class TestValidationNYCAddressInfo(TestCase):
    def test_invalid_state(self):
        with self.assertRaises(ValueError):
            NYCAddressInfo("151 Broome St", "New York", "ny", "10002")

    @patch("meshapi.validation.requests.get")
    def test_validate_address_geosearch_unexpected_responses(self, mock_requests):
        mock_1 = MagicMock()
        mock_1.content = '{"features":[]}'.encode("utf-8")

        mock_2 = MagicMock()
        mock_2.content = "the number 4".encode("utf-8")

        test_cases = [
            {"mock": mock_1, "exception": AddressError},
            {"mock": mock_2, "exception": AddressAPIError},
        ]

        for test_case in test_cases:
            with self.assertRaises(test_case["exception"]):
                mock_requests.return_value = test_case["mock"]
                NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

    @patch("meshapi.validation.requests.get", side_effect=Exception("Pretend this is a network issue"))
    def test_validate_address_geosearch_network(self, mock_requests):
        with self.assertRaises(AddressAPIError):
            NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

    @patch("meshapi.validation.requests.get")
    def test_validate_address_good(self, mock_requests):
        mock_1 = MagicMock()
        mock_1.content = json.dumps(sample_address_response).encode("utf-8")

        mock_2 = MagicMock()
        mock_2.content = "{}".encode("utf-8")

        mock_3 = MagicMock()
        mock_3.content = '[{"heightroof":123.456, "groundelev":76.544}]'.encode("utf-8")

        mock_requests.side_effect = [mock_1, mock_2, mock_3]

        nyc_addr_info = NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

        assert nyc_addr_info is not None
        assert nyc_addr_info.street_address == "151 Broome St"
        assert nyc_addr_info.city == "New York"
        assert nyc_addr_info.state == "NY"
        assert nyc_addr_info.zip == "10002"
        assert nyc_addr_info.longitude == -73.98492
        assert nyc_addr_info.latitude == 40.716245
        assert nyc_addr_info.altitude == 61.0
        assert nyc_addr_info.bin == 1234

    @patch("meshapi.validation.requests.get")
    def test_validate_address_open_data_invalid_response(self, mock_requests):
        mock_series_of_tubes = MagicMock()
        mock_series_of_tubes.content = "a series of tubes".encode("utf-8")

        mock_no_list = MagicMock()
        mock_no_list.content = '{"heightroof":123, "groundelev":456}'.encode("utf-8")

        mock_no_value = MagicMock()
        mock_no_value.content = '[{"heightroof":123}]'.encode("utf-8")

        mock_null_value = MagicMock()
        mock_null_value.content = '[{"heightroof":null, "groundelev":null}]'.encode("utf-8")

        mock_wrong_type = MagicMock()
        mock_wrong_type.content = '[{"heightroof":"a series", "groundelev":"of tubes"}]'.encode("utf-8")

        test_cases = [
            mock_series_of_tubes,
            mock_no_list,
            mock_no_value,
            mock_null_value,
            mock_wrong_type,
            Exception("Pretend this is a network issue"),
        ]

        for mock_test_case in test_cases:
            mock_1 = MagicMock()
            mock_1.content = json.dumps(sample_address_response).encode("utf-8")

            mock_2 = MagicMock()
            mock_2.content = "{}".encode("utf-8")

            mock_requests.side_effect = [mock_1, mock_2, mock_test_case]

            nyc_addr_info = NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

            assert nyc_addr_info is not None
            assert nyc_addr_info.street_address == "151 Broome St"
            assert nyc_addr_info.city == "New York"
            assert nyc_addr_info.state == "NY"
            assert nyc_addr_info.zip == "10002"
            assert nyc_addr_info.longitude == -73.98492
            assert nyc_addr_info.latitude == 40.716245
            assert nyc_addr_info.altitude is None
            assert nyc_addr_info.bin == 1234


class TestValidationOSMAddressInfo(TestCase):
    def test_invalid_state(self):
        with self.assertRaises(ValueError):
            OSMAddressInfo("151 Broome St", "New York", "ny", "10002")

    @patch("meshapi.validation.Nominatim")
    def test_validate_address_geosearch_empty_response(self, mock_nominatim):
        mock_geocode_func = MagicMock()
        mock_geolocator = MagicMock()
        mock_geolocator.geocode = mock_geocode_func
        mock_nominatim.return_value = mock_geolocator

        mock_geocode_func.return_value = None

        with self.assertRaises(AddressError):
            OSMAddressInfo("151 Broome St", "New York", "NY", "10002")

    @patch("meshapi.validation.Nominatim")
    def test_validate_address_geosearch_network_or_throttle(self, mock_nominatim):
        mock_geocode_func = MagicMock()
        mock_geolocator = MagicMock()
        mock_geolocator.geocode = mock_geocode_func
        mock_nominatim.return_value = mock_geolocator
        mock_geocode_func.side_effect = Exception("Pretend this is a network issue")

        with self.assertRaises(AddressAPIError):
            OSMAddressInfo("151 Broome St", "New York", "NY", "10002")

    @patch("meshapi.validation.Nominatim")
    def test_validate_address_good(self, mock_nominatim):
        mock_geocode_func = MagicMock()
        mock_geolocator = MagicMock()
        mock_geolocator.geocode = mock_geocode_func
        mock_nominatim.return_value = mock_geolocator
        mock_geocode_func.return_value = sample_osm_address_response

        osm_addr_info = OSMAddressInfo("151 broome Street", "New York", "NY", "10002")

        assert osm_addr_info is not None
        assert osm_addr_info.osm_id == 250268365
        assert osm_addr_info.osm_place_id == 333450671
        assert osm_addr_info.street_address == "151 Broome Street"
        assert osm_addr_info.city == "New York"
        assert osm_addr_info.state == "NY"
        assert osm_addr_info.zip == "10002"
        assert osm_addr_info.longitude == -73.98489654157149
        assert osm_addr_info.latitude == 40.7162281
        assert osm_addr_info.altitude == INVALID_ALTITUDE


class TestValidationRawAddressInfo(TestCase):
    def test_invalid_state(self):
        with self.assertRaises(TypeError):
            AddressInfo("151 Broome St", "New York", "NY", "10002")

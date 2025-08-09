import json
import logging
from unittest.mock import MagicMock, patch

from django.test import TestCase
from requests import Session
import requests

from meshapi.exceptions import AddressAPIError, InvalidAddressError, UnsupportedAddressError
from meshapi.tests.sample_data import sample_address_response, sample_new_buildings_response
from meshapi.validation import NYCAddressInfo, lookup_address_nyc_open_data_new_buildings


class TestValidationNYCAddressInfo(TestCase):
    def test_invalid_state(self):
        with self.assertRaises(UnsupportedAddressError):
            NYCAddressInfo("151 Broome St", "New York", "ny", "10002")

    @patch.object(Session, 'get')
    def test_validate_address_geosearch_unexpected_responses(self, mock_session):
        mock_1 = MagicMock()
        mock_1.content = '{"features":[]}'.encode("utf-8")

        mock_2 = MagicMock()
        mock_2.content = "the number 4".encode("utf-8")

        test_cases = [
            {"mock": mock_1, "exception": InvalidAddressError},
            {"mock": mock_2, "exception": AddressAPIError},
        ]

        for test_case in test_cases:
            with self.assertRaises(test_case["exception"]):
                mock_session.return_value = test_case["mock"]
                NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

    @patch.object(Session, 'get', side_effect=Exception("Pretend this is a network issue"))
    def test_validate_address_geosearch_network(self, mock_session):
        with self.assertRaises(AddressAPIError):
            NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

    @patch.object(Session, 'get')
    def test_validate_address_good(self, mock_session):
        mock_1 = MagicMock()
        mock_1.content = json.dumps(sample_address_response).encode("utf-8")

        mock_2 = MagicMock()
        mock_2.content = "{}".encode("utf-8")

        mock_3 = MagicMock()
        mock_3.content = '[{"height_roof":123.456, "ground_elevation":76.544}]'.encode("utf-8")

        mock_session.side_effect = [mock_1, mock_2, mock_3]

        nyc_addr_info = NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

        self.assertIsNotNone(nyc_addr_info)
        self.assertEqual(nyc_addr_info.street_address, "151 Broome St")
        self.assertEqual(nyc_addr_info.city, "New York")
        self.assertEqual(nyc_addr_info.state, "NY")
        self.assertEqual(nyc_addr_info.zip, "10002")
        self.assertEqual(nyc_addr_info.longitude, -73.98492)
        self.assertEqual(nyc_addr_info.latitude, 40.716245)
        self.assertEqual(nyc_addr_info.altitude, 61.0)
        self.assertEqual(nyc_addr_info.bin, 1234)

    @patch.object(Session, 'get')
    def test_validate_address_with_nyc_open_data_new_buildings(self, mock_session):
        sample_address_response_invalid_bin = sample_address_response

        # zero out that bin
        sample_address_response_invalid_bin["features"][0]["properties"]["addendum"]["pad"]["bin"] = 1000000

        mock_1 = MagicMock()
        mock_1.content = json.dumps(sample_address_response_invalid_bin).encode("utf-8")

        mock_4 = MagicMock()
        mock_4.json.side_effect = [sample_new_buildings_response]
        mock_4.status_code = 200

        mock_2 = MagicMock()
        mock_2.content = "{}".encode("utf-8")

        mock_3 = MagicMock()
        mock_3.content = '[{"height_roof":123.456, "ground_elevation":76.544}]'.encode("utf-8")

        mock_session.side_effect = [mock_1, mock_2, mock_4, mock_3]

        nyc_addr_info = NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

        self.assertIsNotNone(nyc_addr_info)
        self.assertEqual(nyc_addr_info.street_address, "151 Broome St")
        self.assertEqual(nyc_addr_info.city, "New York")
        self.assertEqual(nyc_addr_info.state, "NY")
        self.assertEqual(nyc_addr_info.zip, "10002")
        self.assertEqual(nyc_addr_info.longitude, -73.98492)
        self.assertEqual(nyc_addr_info.latitude, 40.716245)
        self.assertEqual(nyc_addr_info.altitude, 61.0)
        self.assertEqual(nyc_addr_info.bin, 1234)

    @patch.object(Session, 'get')
    def test_validate_address_with_nyc_open_data_new_buildings_different_bin(self, mock_session):
        sample_address_response_invalid_bin = sample_address_response

        # zero out that bin
        sample_address_response_invalid_bin["features"][0]["properties"]["addendum"]["pad"]["bin"] = 1000000

        mock_1 = MagicMock()
        mock_1.content = json.dumps(sample_address_response_invalid_bin).encode("utf-8")

        sample_new_buildings_response_different_bin = sample_new_buildings_response.copy()
        sample_new_buildings_response_different_bin.append(sample_new_buildings_response_different_bin[0].copy())
        sample_new_buildings_response_different_bin[1]["bin__"] = "5678"

        mock_4 = MagicMock()
        mock_4.json.side_effect = [sample_new_buildings_response_different_bin]
        mock_4.status_code = 200

        mock_2 = MagicMock()
        mock_2.content = "{}".encode("utf-8")

        mock_3 = MagicMock()
        mock_3.content = '[{"height_roof":123.456, "ground_elevation":76.544}]'.encode("utf-8")

        mock_session.side_effect = [mock_1, mock_2, mock_4, mock_3]

        with self.assertRaises(AddressAPIError):
            _ = NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

    @patch.object(Session, 'get')
    def test_validate_address_with_nyc_open_data_new_buildings_none_response(self, mock_session):
        sample_address_response_invalid_bin = sample_address_response

        # zero out that bin
        sample_address_response_invalid_bin["features"][0]["properties"]["addendum"]["pad"]["bin"] = 1000000

        mock_1 = MagicMock()
        mock_1.content = json.dumps(sample_address_response_invalid_bin).encode("utf-8")

        sample_new_buildings_response_different_bin = sample_new_buildings_response.copy()
        sample_new_buildings_response_different_bin.append(sample_new_buildings_response_different_bin[0].copy())
        sample_new_buildings_response_different_bin[1]["bin__"] = "5678"

        mock_4 = MagicMock()
        mock_4.json.side_effect = [[]]
        mock_4.status_code = 200

        mock_2 = MagicMock()
        mock_2.content = "{}".encode("utf-8")

        mock_3 = MagicMock()
        mock_3.content = '[{"height_roof":123.456, "ground_elevation":76.544}]'.encode("utf-8")

        mock_session.side_effect = [mock_1, mock_2, mock_4, mock_3]

        with self.assertRaises(InvalidAddressError):
            _ = NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

    @patch.object(Session, 'get')
    def test_lookup_address_nyc_open_data_new_buildings_with_no_response(self, mock_session):
        sample_new_buildings_response_different_bin = sample_new_buildings_response.copy()
        sample_new_buildings_response_different_bin.append(sample_new_buildings_response_different_bin[0].copy())
        sample_new_buildings_response_different_bin[1]["bin__"] = "5678"

        mock_1 = MagicMock()
        mock_1.json.side_effect = [[]]
        mock_1.status_code = 200

        # This has to be a Response and not a MagicMock because we're using
        # raise_for_status
        mock_2 = requests.Response()
        mock_2.status_code = 503

        mock_session.side_effect = [mock_1, mock_2]

        open_data_bin = lookup_address_nyc_open_data_new_buildings("chom", "skz", "skal", "sklad")
        self.assertIsNone(open_data_bin, "Did not get None response when receiving an empty response from New Buildings API.")

        open_data_bin = lookup_address_nyc_open_data_new_buildings("chom", "skz", "skal", "sklad")
        self.assertIsNone(open_data_bin, "Did not get None response when receiving a 503 from New Buildings API.")

    @patch.object(Session, 'get')
    def test_validate_address_open_data_invalid_response(self, mock_session):
        mock_series_of_tubes = MagicMock()
        mock_series_of_tubes.content = "a series of tubes".encode("utf-8")

        mock_no_list = MagicMock()
        mock_no_list.content = '{"height_roof":123, "ground_elevation":456}'.encode("utf-8")

        mock_no_value = MagicMock()
        mock_no_value.content = '[{"height_roof":123}]'.encode("utf-8")

        mock_null_value = MagicMock()
        mock_null_value.content = '[{"height_roof":null, "ground_elevation":null}]'.encode("utf-8")

        mock_wrong_type = MagicMock()
        mock_wrong_type.content = '[{"height_roof":"a series", "ground_elevation":"of tubes"}]'.encode("utf-8")

        test_cases = {
            "a series of tubes": mock_series_of_tubes,
            "no list": mock_no_list,
            "no value": mock_no_value,
            "null value": mock_null_value,
            "wrong type": mock_wrong_type,
            "network issue": Exception("Pretend this is a network issue"),
        }

        for title, mock_test_case in test_cases.items():
            logging.info(title)
            mock_1 = MagicMock()
            mock_1.content = json.dumps(sample_address_response).encode("utf-8")

            mock_2 = MagicMock()
            mock_2.content = "{}".encode("utf-8")

            mock_session.side_effect = [mock_1, mock_2, mock_test_case]

            nyc_addr_info = NYCAddressInfo("151 Broome St", "New York", "NY", "10002")

            self.assertIsNotNone(nyc_addr_info)
            self.assertEqual(nyc_addr_info.street_address, "151 Broome St")
            self.assertEqual(nyc_addr_info.city, "New York")
            self.assertEqual(nyc_addr_info.state, "NY")
            self.assertEqual(nyc_addr_info.zip, "10002")
            self.assertEqual(nyc_addr_info.longitude, -73.98492)
            self.assertEqual(nyc_addr_info.latitude, 40.716245)
            self.assertEqual(nyc_addr_info.altitude, None)
            self.assertEqual(nyc_addr_info.bin, 1234)

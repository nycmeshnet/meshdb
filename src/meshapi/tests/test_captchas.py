import unittest.mock as mock

import pytest
import requests_mock
from django.test import TestCase

from meshapi.validation import RECAPTCHA_TOKEN_VALIDATION_URL, check_recaptcha_token, validate_recaptcha_tokens


class TestHelpers(TestCase):
    @requests_mock.Mocker()
    def test_check_recaptcha_v2_token_success(self, request_mocker):
        request_mocker.post(
            RECAPTCHA_TOKEN_VALIDATION_URL,
            json={
                "success": True,
                "challenge_ts": "2024-11-16T20:52:23ZZ",
                "hostname": "forms.nycmesh.net",
                "score": 0.4,
            },
        )
        score = check_recaptcha_token("fake_token", "fake_secret", "0.0.0.0")
        self.assertEqual(score, 0.4)

        self.assertEqual(len(request_mocker.request_history), 1)
        self.assertEqual(
            request_mocker.request_history[0].url,
            RECAPTCHA_TOKEN_VALIDATION_URL,
        )
        self.assertEqual(
            request_mocker.request_history[0].text,
            "secret=fake_secret&response=fake_token&remoteip=0.0.0.0",
        )

    @requests_mock.Mocker()
    def test_check_recaptcha_v3_token_success(self, request_mocker):
        request_mocker.post(
            RECAPTCHA_TOKEN_VALIDATION_URL,
            json={
                "success": True,
                "challenge_ts": "2024-11-16T20:52:23ZZ",
                "hostname": "forms.nycmesh.net",
            },
        )
        score = check_recaptcha_token("fake_token", "fake_secret", None)
        self.assertEqual(score, 1.0)

        self.assertEqual(len(request_mocker.request_history), 1)
        self.assertEqual(
            request_mocker.request_history[0].url,
            RECAPTCHA_TOKEN_VALIDATION_URL,
        )
        self.assertEqual(
            request_mocker.request_history[0].text,
            "secret=fake_secret&response=fake_token",
        )

    @requests_mock.Mocker()
    def test_check_recaptcha_token_invalid_token(self, request_mocker):
        request_mocker.post(
            RECAPTCHA_TOKEN_VALIDATION_URL,
            json={
                "success": False,
                "challenge_ts": "2024-11-16T20:52:23ZZ",
                "hostname": "forms.nycmesh.net",
            },
        )

        with pytest.raises(ValueError):
            check_recaptcha_token("bad_token", "fake_secret", None)

        self.assertEqual(len(request_mocker.request_history), 1)
        self.assertEqual(
            request_mocker.request_history[0].url,
            RECAPTCHA_TOKEN_VALIDATION_URL,
        )
        self.assertEqual(
            request_mocker.request_history[0].text,
            "secret=fake_secret&response=bad_token",
        )

    @mock.patch("meshapi.validation.check_recaptcha_token")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V2", "fake_secret_v2")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V3", "fake_secret_v3")
    def test_validate_token_good_invisible(self, mock_check_recaptcha_token):
        mock_check_recaptcha_token.return_value = 0.6
        validate_recaptcha_tokens("invisible_token", None, None)
        mock_check_recaptcha_token.assert_called_once_with("invisible_token", "fake_secret_v3", None)

    @mock.patch("meshapi.validation.check_recaptcha_token")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V2", "fake_secret_v2")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V3", "fake_secret_v3")
    def test_validate_token_bad_invisible(self, mock_check_recaptcha_token):
        mock_check_recaptcha_token.return_value = 0.3
        with pytest.raises(ValueError):
            validate_recaptcha_tokens("invisible_token", None, None)

        mock_check_recaptcha_token.assert_called_once_with("invisible_token", "fake_secret_v3", None)

    @mock.patch("meshapi.validation.check_recaptcha_token")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V2", "fake_secret_v2")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V3", "fake_secret_v3")
    def test_validate_token_good_checkbox(self, mock_check_recaptcha_token):
        mock_check_recaptcha_token.return_value = 1.0
        validate_recaptcha_tokens("invisible_token", "checkbox_token", None)
        mock_check_recaptcha_token.assert_called_once_with("checkbox_token", "fake_secret_v2", None)

    @mock.patch("meshapi.validation.check_recaptcha_token")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V2", "fake_secret_v2")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V3", "fake_secret_v3")
    def test_validate_token_invalid_checkbox(self, mock_check_recaptcha_token):
        mock_check_recaptcha_token.side_effect = ValueError()
        with pytest.raises(ValueError):
            validate_recaptcha_tokens("invisible_token", "checkbox_token", None)
        mock_check_recaptcha_token.assert_called_once_with("checkbox_token", "fake_secret_v2", None)

    @mock.patch("meshapi.validation.check_recaptcha_token")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V2", "fake_secret_v2")
    @mock.patch("meshapi.validation.RECAPTCHA_SECRET_KEY_V3", "fake_secret_v3")
    def test_validate_token_invalid_invisible(self, mock_check_recaptcha_token):
        mock_check_recaptcha_token.side_effect = ValueError()
        with pytest.raises(ValueError):
            validate_recaptcha_tokens("invisible_token", None, None)
        mock_check_recaptcha_token.assert_called_once_with("invisible_token", "fake_secret_v3", None)

    def test_validate_token_no_env_vars(self):
        with pytest.raises(EnvironmentError):
            validate_recaptcha_tokens("invisible_token", None, None)

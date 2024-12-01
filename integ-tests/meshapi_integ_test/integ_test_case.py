import os
import unittest

import requests
from dotenv import load_dotenv

load_dotenv()

SITE_BASE_URL = os.environ["SITE_BASE_URL"]
INTEG_TEST_MESHDB_API_TOKEN = os.environ["INTEG_TEST_MESHDB_API_TOKEN"]


class IntegTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.authed_session = requests.Session()
        self.authed_session.headers = {"Authorization": f"Bearer {INTEG_TEST_MESHDB_API_TOKEN}"}

    def get_url(self, url_path):
        return SITE_BASE_URL + url_path

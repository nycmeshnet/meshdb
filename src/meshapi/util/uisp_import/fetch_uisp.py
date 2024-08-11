import json
import os
from typing import List, Optional

import requests
from dotenv import load_dotenv

from meshapi.util.uisp_import.types.data_links import DataLink as UISPDataLink
from meshapi.util.uisp_import.types.devices import Device as UISPDevice

load_dotenv()


UISP_URL = os.environ["UISP_URL"]
UISP_USER = os.environ["UISP_USER"]
UISP_PASS = os.environ["UISP_PASS"]


def get_uisp_devices() -> List[UISPDevice]:
    session = get_uisp_session()

    return json.loads(
        session.get(
            os.path.join(UISP_URL, "api/v2.1/devices"),
            verify=False,
        ).content.decode("UTF8")
    )


def get_uisp_links() -> List[UISPDataLink]:
    session = get_uisp_session()

    return json.loads(
        session.get(
            os.path.join(UISP_URL, "api/v2.1/data-links"),
            verify=False,
        ).content.decode("UTF8")
    )


def get_uisp_device_detail(device_id: str, session: Optional[requests.Session] = None) -> UISPDevice:
    if not session:
        session = get_uisp_session()

    return json.loads(
        session.get(
            os.path.join(UISP_URL, f"api/v2.1/devices/{device_id}"),
            verify=False,
        ).content.decode("UTF8")
    )


def get_uisp_token(session: requests.Session) -> str:
    return session.post(
        os.path.join(UISP_URL, "api/v2.1/user/login"),
        json={
            "username": UISP_USER,
            "password": UISP_PASS,
        },
        verify=False,
    ).headers["x-auth-token"]


def get_uisp_session() -> requests.Session:
    session = requests.Session()
    session.headers = {"x-auth-token": get_uisp_token(session)}

    return session

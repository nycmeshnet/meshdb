import json
import os
from typing import List, Optional

import requests
from dotenv import load_dotenv

from meshapi.types.uisp_api.data_links import DataLink as UISPDataLink
from meshapi.types.uisp_api.devices import Device as UISPDevice
load_dotenv()

from meshdb.environment import UISP_URL,UISP_USER,UISP_PASS



def get_uisp_devices() -> List[UISPDevice]:
    session = get_uisp_session()

    if not UISP_URL:
        raise EnvironmentError("Missing UISP_URL, please set it via an environment variable")

    return json.loads(
        session.get(
            os.path.join(UISP_URL, "api/v2.1/devices"),
        ).content.decode("UTF8")
    )


def get_uisp_links() -> List[UISPDataLink]:
    session = get_uisp_session()

    if not UISP_URL:
        raise EnvironmentError("Missing UISP_URL, please set it via an environment variable")

    return json.loads(
        session.get(
            os.path.join(UISP_URL, "api/v2.1/data-links"),
        ).content.decode("UTF8")
    )


def get_uisp_device_detail(device_id: str, session: Optional[requests.Session] = None) -> UISPDevice:
    if not session:
        session = get_uisp_session()

    if not UISP_URL:
        raise EnvironmentError("Missing UISP_URL, please set it via an environment variable")

    return json.loads(
        session.get(
            os.path.join(UISP_URL, f"api/v2.1/devices/{device_id}"),
        ).content.decode("UTF8")
    )


def get_uisp_token(session: requests.Session) -> str:
    if not UISP_URL:
        raise EnvironmentError("Missing UISP_URL, please set it via an environment variable")

    return session.post(
        os.path.join(UISP_URL, "api/v2.1/user/login"),
        json={
            "username": UISP_USER,
            "password": UISP_PASS,
        },
    ).headers["x-auth-token"]


def get_uisp_session() -> requests.Session:
    session = requests.Session()
    session.verify = os.path.join(os.path.dirname(__file__), "uisp.mesh.nycmesh.net.crt")
    session.headers = {"x-auth-token": get_uisp_token(session)}

    return session

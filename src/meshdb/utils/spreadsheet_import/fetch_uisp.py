import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()


def download_uisp_devices():
    session = get_uisp_session()

    return json.loads(
        session.get(
            os.path.join(os.environ["UISP_URL"], "api/v2.1/devices"),
            verify=False,
        ).content.decode("UTF8")
    )


def download_uisp_links():
    session = get_uisp_session()

    return json.loads(
        session.get(
            os.path.join(os.environ["UISP_URL"], "api/v2.1/data-links"),
            verify=False,
        ).content.decode("UTF8")
    )


def uisp_login(session: requests.Session):
    return session.post(
        os.path.join(os.environ["UISP_URL"], "api/v2.1/user/login"),
        json={
            "username": os.environ["UISP_USER"],
            "password": os.environ["UISP_PASS"],
        },
        verify=False,
    ).headers["x-auth-token"]


def get_uisp_session():
    session = requests.Session()
    session.headers = {"x-auth-token": uisp_login(session)}

    return session

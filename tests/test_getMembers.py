import pytest
import requests
import json


@pytest.fixture(autouse=True)
def fixture_login():
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    params = {"include_auth_token": "true"}
    data = {"email": "example@nycmesh.net", "password": "abcd1234"}
    response = requests.post(
        "http://localhost:8080/login",
        headers=headers,
        params=params,
        data=json.dumps(data),
        timeout=3,
    )
    return response


def test_getMembers(fixture_login):
    authentication_token = fixture_login.json()["response"]["user"]["authentication_token"]
    response = requests.get(
        "http://localhost:8080/getMembers",
        headers={"content-type": "application/json", "Authentication-Token": authentication_token},
        timeout=3,
    )
    assert response.status_code == 200
    assert response.json()[0]["emailAddress"] == "dheredia@nycmesh.net"

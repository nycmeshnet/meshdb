import pytest
import requests


def test_getMembers():
    response = requests.get("http://localhost:8080/getMembers", data={"firstname": "Daniel", "lastname": "Heredia"})
    print(response.content)
    assert response.status_code == 200

import pytest
import requests


def test_getMembers():
    response = requests.get("http://localhost:8080/getMembers")
    assert response.status_code == 200

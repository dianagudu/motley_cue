import pytest
import os
from starlette.testclient import TestClient

from motley_cue.api import api


@pytest.fixture(scope="module")
def test_api():
    client = TestClient(api)
    yield client  # testing happens here


@pytest.fixture(scope="module")
def test_api_with_token():
    token = os.getenv("EGI_TOKEN")
    client = TestClient(api)
    yield client, token  # testing happens here

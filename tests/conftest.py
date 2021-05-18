import pytest
from starlette.testclient import TestClient

from motley_cue.api import api


@pytest.fixture(scope="module")
def test_api():
    client = TestClient(api)
    yield client  # testing happens here

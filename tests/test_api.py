import pytest

from .utils import PUBLIC_ENDPOINTS, PROTECTED_ENDPOINTS


@pytest.mark.parametrize(
    "endpoint,keys,children",
    [(x.endpoint, x.keys, x.children) for x in PUBLIC_ENDPOINTS],
    ids=[x.endpoint for x in PUBLIC_ENDPOINTS]
)
def test_public_endpoints(test_api, endpoint, keys, children):
    response = test_api.get(endpoint)
    assert response.status_code == 200
    assert set(response.json().keys()) == set(keys)
    if children:
        assert set(response.json()["endpoints"].keys()) == set(
            [child.endpoint for child in children]
        )


@pytest.mark.parametrize(
    "endpoint",
    [x.endpoint for x in PROTECTED_ENDPOINTS]
)
def test_protected_endpoints(test_api, endpoint):
    response = test_api.get(endpoint)
    assert response.status_code == 403

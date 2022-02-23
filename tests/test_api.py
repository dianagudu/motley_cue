import pytest

from .utils import PUBLIC_ENDPOINTS, PROTECTED_ENDPOINTS, QUERY_ENDPOINTS, Info
from .utils import MC_HEADERS, build_query_string
from .test_env import MC_ISS
from .configs import CONFIG_AUTHORISE_ALL, CONFIG_SUPPORTED_NOT_AUTHORISED, CONFIG_DOC_ENABLED, CONFIG_CUSTOM_DOC


@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED])
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, "", e.callback_valid) for e in PUBLIC_ENDPOINTS],
    ids=[x.url for x in PUBLIC_ENDPOINTS])
def test_public_endpoints_no_patch(test_api, endpoint):
    response = test_api.get(endpoint.url)
    assert response.status_code == 200
    assert set(response.json().keys()) == set(endpoint.valid_response.keys())
    if endpoint.children:
        assert set(response.json()["endpoints"].keys()) == set(
            [child.url for child in endpoint.children]
        )
    # for the info endpoint, check for correct info
    if endpoint == Info:
        assert [url.rstrip("/") for url in response.json()["supported_OPs"]] == [MC_ISS.rstrip("/")]


@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED])
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, e.mapper_method, e.callback_valid) for e in PROTECTED_ENDPOINTS],
    ids=[x.url for x in PROTECTED_ENDPOINTS])
def test_protected_endpoints_missing_token(test_api, endpoint):
    response = test_api.get(endpoint.url)
    assert response.status_code == 403


@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED])
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, e.mapper_method, e.callback_valid) for e in QUERY_ENDPOINTS],
    ids=[x.url for x in QUERY_ENDPOINTS])
def test_query_endpoints_missing_params(test_api, endpoint):
    response = test_api.get(endpoint.url, headers=MC_HEADERS)
    assert response.status_code == 400


@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED])
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, e.mapper_method, e.callback_valid) for e in PROTECTED_ENDPOINTS],
    ids=[x.url for x in PROTECTED_ENDPOINTS])
def test_protected_endpoints_with_token(test_api, endpoint):
    params = {x: "" for x in endpoint.params}
    response = test_api.get(
        "{}?{}".format(endpoint.url, build_query_string(params)),
        headers=MC_HEADERS
    )
    assert response.status_code == 200


@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED])
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, e.mapper_method, lambda *x: {}) for e in PROTECTED_ENDPOINTS],
    ids=[x.url for x in PROTECTED_ENDPOINTS])
def test_invalid_response_models(test_api, endpoint):
    params = {x: "" for x in endpoint.params}
    response = test_api.get(
        "{}?{}".format(endpoint.url, build_query_string(params)),
        headers=MC_HEADERS
    )
    assert response.status_code == 500


@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED])
@pytest.mark.parametrize("method_to_patch,callback", [("", lambda *x: {})])
def test_no_doc_apis(test_api):
    response = test_api.get("/docs")
    assert response.status_code == 404
    response = test_api.get("/redoc")
    assert response.status_code == 404
    response = test_api.get("/openapi.json")
    assert response.status_code == 200


@pytest.mark.parametrize("config_file,doc_url",
    [(CONFIG_DOC_ENABLED, "/docs"), (CONFIG_CUSTOM_DOC, "/api/v1/docs")],
    ids=["docs_enabled", "custom_docs"])
@pytest.mark.parametrize("method_to_patch,callback", [("", lambda *x: {})], ids=[""])
def test_doc_apis(test_api, doc_url):
    response = test_api.get(doc_url)
    assert response.status_code == 200
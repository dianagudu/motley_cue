import pytest
import sys
from pydantic import ValidationError

from .utils import (
    PUBLIC_ENDPOINTS,
    PROTECTED_ENDPOINTS,
    QUERY_ENDPOINTS,
    Info,
    InfoOp,
    build_query_string,
)
from .utils import MOCK_HEADERS, MOCK_ISS
from .configs import CONFIGS_AUTHENTICATED_USERS, CONFIG_NOT_SUPPORTED
from .configs import CONFIG_DOC_ENABLED, CONFIG_CUSTOM_DOC, CONFIG_INVALID_CUSTOM_DOC


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, "", e.callback_valid) for e in PUBLIC_ENDPOINTS],
    ids=[x.url for x in PUBLIC_ENDPOINTS],
)
def test_public_endpoints_no_patch(test_api, endpoint):
    response = test_api.get(endpoint.url)
    assert response.status_code == 200
    assert set(response.json().keys()) == set(endpoint.valid_response.keys())
    if endpoint.children:
        assert set(response.json()["endpoints"].keys()) == set(
            [child.url for child in endpoint.children]
        )


@pytest.mark.parametrize(
    "config_file,supported_ops",
    [
        *[(cf, [MOCK_ISS.rstrip("/")]) for cf in CONFIGS_AUTHENTICATED_USERS.values()],
        (CONFIG_NOT_SUPPORTED, []),
    ],
    ids=[*CONFIGS_AUTHENTICATED_USERS.keys(), "NOT_SUPPORTED"],
)
@pytest.mark.parametrize("method_to_patch,callback", [("", Info.callback_valid)])
def test_info_endpoint(test_api, supported_ops):
    response = test_api.get(Info.url)
    assert [url.rstrip("/") for url in response.json()["supported_OPs"]] == supported_ops


@pytest.mark.parametrize(
    "config_file",
    [
        *CONFIGS_AUTHENTICATED_USERS.values(),
        CONFIG_NOT_SUPPORTED,
    ],
    ids=[*CONFIGS_AUTHENTICATED_USERS.keys(), "NOT_SUPPORTED"],
)
@pytest.mark.parametrize("method_to_patch,callback", [("", InfoOp.callback_valid)])
def test_info_op_not_supported(test_api):
    params = {param: "INVALID_PARAM" for param in InfoOp.params}
    response = test_api.get("{}?{}".format(InfoOp.url, build_query_string(params)))
    assert response.status_code == 404


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, e.mapper_method, e.callback_valid) for e in PROTECTED_ENDPOINTS],
    ids=[x.url for x in PROTECTED_ENDPOINTS],
)
def test_protected_endpoints_missing_token(test_api, endpoint):
    response = test_api.get(endpoint.url)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, e.mapper_method, e.callback_valid) for e in QUERY_ENDPOINTS],
    ids=[x.url for x in QUERY_ENDPOINTS],
)
def test_query_endpoints_missing_params(test_api, endpoint):
    response = test_api.get(endpoint.url, headers=MOCK_HEADERS)
    assert response.status_code == 400


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, e.mapper_method, e.callback_valid) for e in PROTECTED_ENDPOINTS],
    ids=[x.url for x in PROTECTED_ENDPOINTS],
)
def test_protected_endpoints_with_token(test_api, endpoint):
    params = {x: "" for x in endpoint.params}
    response = test_api.get(
        "{}?{}".format(endpoint.url, build_query_string(params)), headers=MOCK_HEADERS
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
@pytest.mark.parametrize(
    "endpoint,method_to_patch,callback",
    [(e, e.mapper_method, lambda *x: {}) for e in PROTECTED_ENDPOINTS],
    ids=[x.url for x in PROTECTED_ENDPOINTS],
)
def test_invalid_response_models(test_api, endpoint):
    params = {x: "" for x in endpoint.params}
    response = test_api.get(
        "{}?{}".format(endpoint.url, build_query_string(params)), headers=MOCK_HEADERS
    )
    assert response.status_code == 500


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
@pytest.mark.parametrize("method_to_patch,callback", [("", lambda *x: {})])
def test_no_doc_apis(test_api):
    response = test_api.get("/docs")
    assert response.status_code == 404
    response = test_api.get("/redoc")
    assert response.status_code == 404
    response = test_api.get("/openapi.json")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "config_file,doc_url",
    [(CONFIG_DOC_ENABLED, "/docs"), (CONFIG_CUSTOM_DOC, "/api/v1/docs")],
    ids=["docs_enabled", "custom_docs"],
)
@pytest.mark.parametrize("method_to_patch,callback", [("", lambda *x: {})], ids=[""])
def test_doc_apis(test_api, doc_url):
    response = test_api.get(doc_url)
    assert response.status_code == 200


@pytest.mark.parametrize("config_file", [CONFIG_INVALID_CUSTOM_DOC])
def test_api_invalid_config(config_file, monkeypatch):
    with monkeypatch.context() as mp:
        # patch the config to return minimal config instead of reading through files
        from motley_cue.mapper import config

        mp.setattr(config.Config, "from_files", lambda x: config.Config(config_file))

        with pytest.raises(ValidationError):
            # import FastAPI object here to make sure its decorators are based on monkeypatched mapper
            from motley_cue.api import api

        # unload all motley_cue modules
        for m in [x for x in sys.modules if x.startswith("motley_cue")]:
            del sys.modules[m]

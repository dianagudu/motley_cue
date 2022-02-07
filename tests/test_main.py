from .utils import ROOT_KEYS, ROOT_ENDPOINTS
from .utils import USER_ENDPOINTS, ADMIN_ENDPOINTS
from .utils import INFO_KEYS, INFO_AUTHZ_KEYS


def test_root(test_api):
    response = test_api.get("/")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(ROOT_KEYS)
    assert set(response.json()["endpoints"].keys()) == set(ROOT_ENDPOINTS)


def test_user_root(test_api):
    response = test_api.get("/user")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(ROOT_KEYS)
    assert set(response.json()["endpoints"].keys()) == set(USER_ENDPOINTS)


def test_admin_root(test_api):
    response = test_api.get("/admin")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(ROOT_KEYS)
    assert set(response.json()["endpoints"].keys()) == set(ADMIN_ENDPOINTS)


def test_info(test_api):
    response = test_api.get("/info")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(INFO_KEYS)


def test_forbidden_info_authorisation(test_api):
    response = test_api.get("/info/authorisation")
    assert response.status_code == 403


def test_forbidden_verify_user(test_api):
    response = test_api.get("/verify_user")
    assert response.status_code == 403


def test_forbidden_user_endpoints(test_api):
    for endpoint in USER_ENDPOINTS:
        response = test_api.get(f"/user{endpoint}")
        assert response.status_code == 403


def test_forbidden_admin_endpoints(test_api):
    for endpoint in ADMIN_ENDPOINTS:
        response = test_api.get(f"/admin{endpoint}")
        assert response.status_code == 403


def test_bad_token_info_authorisation(test_api):
    token = "BADTOKEN"
    headers = {"Authorization": f"Bearer {token}"}
    response = test_api.get("/info/authorisation", headers=headers)
    assert response.status_code == 401


def test_login_info_authorisation(test_api_with_token):
    test_api, token = test_api_with_token
    headers = {"Authorization": f"Bearer {token}"}
    response = test_api.get("/info/authorisation", headers=headers)
    assert response.status_code == 200
    assert set(response.json().keys()).issuperset(
        set(INFO_AUTHZ_KEYS))
from .utils import *


def test_public_endpoints(test_api):
    response = test_api.get("/")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(ROOT_KEYS)
    assert set(response.json()["endpoints"].keys()) == set(ROOT_ENDPOINTS)

    response = test_api.get("/user")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(ROOT_KEYS)
    assert set(response.json()["endpoints"].keys()) == set(USER_ENDPOINTS)

    response = test_api.get("/admin")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(ROOT_KEYS)
    assert set(response.json()["endpoints"].keys()) == set(ADMIN_ENDPOINTS)

    response = test_api.get("/info")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(INFO_KEYS)


def test_protected_endpoints_forbidden(test_api):
    response = test_api.get("/info/authorisation")
    assert response.status_code == 403

    response = test_api.get("/verify_user")
    assert response.status_code == 403

    for endpoint in USER_ENDPOINTS:
        response = test_api.get(f"/user{endpoint}")
        assert response.status_code == 403

    for endpoint in ADMIN_ENDPOINTS:
        response = test_api.get(f"/admin{endpoint}")
        assert response.status_code == 403


def test_bad_token(test_api):
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

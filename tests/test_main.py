def test_root(test_api):
    response = test_api.get("/")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(
        ["description", "endpoints", "usage"])
    assert set(response.json()["endpoints"].keys()) == set(
        ["/info", "/info/authorisation", "/user", "/admin", "/verify_user"]
    )


def test_info(test_api):
    response = test_api.get("/info")
    assert response.status_code == 200
    assert set(response.json().keys()) == set(["login info", "supported OPs"])


def test_info_authorisation(test_api):
    response = test_api.get("/info/authorisation")
    assert response.status_code == 403

import pytest

from motley_cue.dependencies import mapper
from .utils import InfoAuthorisation, TOKEN


@pytest.mark.parametrize("token,status_code,info_str", [
    (TOKEN["BADTOKEN"], 401, None),
    (TOKEN["NOT_SUPPORTED"], 401, None),
    (TOKEN["SUPPORTED_NOT_AUTHORISED"], 200, "supported but not authorised"),
    (TOKEN["AUTHORISE_ALL"], 200, "authorise all"),
    (TOKEN["VO_BASED"], 200, "VO-based authorisation"),
    (TOKEN["INDIVIDUAL"], 200, "individual authorisation")
], ids=TOKEN.keys())
def test_info_authorisation(test_api, token, status_code, info_str):
    headers = {"Authorization": f"Bearer {token}"}
    response = test_api.get(InfoAuthorisation.endpoint, headers=headers)
    assert response.status_code == status_code
    if info_str:
        assert set(response.json().keys()).issuperset(
            set(InfoAuthorisation.keys))
        assert response.json()["info"] == info_str


@pytest.mark.parametrize("token,status_code", [
    (TOKEN["BADTOKEN"], 401),
    (TOKEN["NOT_SUPPORTED"], 403),
    (TOKEN["SUPPORTED_NOT_AUTHORISED"], 403),
    (TOKEN["AUTHORISE_ALL"], 200),
    (TOKEN["VO_BASED"], 200),
    (TOKEN["INDIVIDUAL"], 200)
], ids=TOKEN.keys())
def test_require_authorised_user(test_api, monkeypatch, token, status_code):
    def mock_get_status(request):
        return {"test": "OK"}
    monkeypatch.setattr(mapper, "get_status", mock_get_status)
    headers = {"Authorization": f"Bearer {token}"}
    response = test_api.get("/user/get_status", headers=headers)
    assert response.status_code == status_code
    if status_code == 200:
        assert response.json()["test"] == "OK"

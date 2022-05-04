from typing import Dict
import pytest

from .utils import (
    InfoAuthorisation,
    MOCK_REQUEST,
    MOCK_BAD_REQUEST,
    MOCK_ISS,
    MOCK_SUB,
    MOCK_TOKEN,
)
from .configs import (
    CONFIGS,
    CONFIGS_AUTHENTICATED_USERS,
    CONFIGS_AUTHORISED_USERS,
    CONFIGS_AUTHORISED_ADMINS,
)


async def view_func(*args, **kwargs):
    return {"message": "Success"}


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
def test_info_authorisation(test_authorisation):
    response = test_authorisation.info(MOCK_REQUEST)
    assert set(InfoAuthorisation.valid_response.keys()) <= set(response.keys())


@pytest.mark.parametrize("config_file", [CONFIGS["NOT_SUPPORTED"]], ids=["NOT_SUPPORTED"])
def test_info_authorisation_not_supported(test_authorisation, test_unauthorised):
    with pytest.raises(test_unauthorised):
        test_authorisation.info(MOCK_REQUEST)


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHORISED_USERS.values(),
    ids=CONFIGS_AUTHORISED_USERS.keys(),
)
async def test_require_authorised_user_success(test_authorisation):
    assert await test_authorisation.authorised_user_required(view_func)(request=MOCK_REQUEST) == {
        "message": "Success"
    }


@pytest.mark.parametrize(
    "config_file,status_code",
    [
        (CONFIGS["SUPPORTED_NOT_AUTHORISED"], 403),
        (CONFIGS["NOT_SUPPORTED"], 401),
    ],
    ids=["SUPPORTED_NOT_AUTHORISED", "NOT_SUPPORTED"],
)
async def test_require_authorised_user_fail(test_authorisation, status_code):
    response = await test_authorisation.authorised_user_required(view_func)(request=MOCK_REQUEST)
    assert response.status_code == status_code


@pytest.mark.parametrize("config_file", CONFIGS.values(), ids=CONFIGS.keys())
async def test_require_authorised_user_bad_request(test_authorisation):
    response = await test_authorisation.authorised_user_required(view_func)(
        request=MOCK_BAD_REQUEST
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "config_file,iss",
    [
        (CONFIGS["ADMIN"], MOCK_ISS),
        (CONFIGS["ADMIN_FOR_ALL"], MOCK_ISS),
        (CONFIGS["ADMIN_FOR_ALL"], "anything"),
    ],
)
async def test_require_authorised_admin_success(test_authorisation, iss):
    assert await test_authorisation.authorised_admin_required(view_func)(
        request=MOCK_REQUEST, iss=iss
    ) == {"message": "Success"}


@pytest.mark.parametrize(
    "config_file,status_code",
    [
        (CONFIGS["ADMIN"], 403),
        (CONFIGS["SUPPORTED_NOT_AUTHORISED"], 403),
        (CONFIGS["NOT_SUPPORTED"], 401),
    ],
    ids=["ADMIN", "SUPPORTED_NOT_AUTHORISED", "NOT_SUPPORTED"],
)
async def test_require_authorised_admin_fail(test_authorisation, status_code):
    response = await test_authorisation.authorised_admin_required(view_func)(
        request=MOCK_REQUEST, iss="anything"
    )
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHORISED_ADMINS.values(),
    ids=CONFIGS_AUTHORISED_ADMINS.keys(),
)
async def test_require_authorised_admin_bad_request(test_authorisation):
    response = await test_authorisation.authorised_admin_required(view_func)(
        request=MOCK_BAD_REQUEST, iss="anything"
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
async def test_require_authenticated_user_success(test_authorisation):
    assert await test_authorisation.authenticated_user_required(view_func)(
        request=MOCK_REQUEST
    ) == {"message": "Success"}


@pytest.mark.parametrize("config_file", [CONFIGS["NOT_SUPPORTED"]], ids=["NOT_SUPPORTED"])
async def test_require_authenticated_user_fail(test_authorisation):
    response = await test_authorisation.authenticated_user_required(view_func)(request=MOCK_REQUEST)
    assert response.status_code == 401


@pytest.mark.parametrize("config_file", CONFIGS.values(), ids=CONFIGS.keys())
async def test_require_authenticated_user_bad_request(test_authorisation):
    response = await test_authorisation.authenticated_user_required(view_func)(
        request=MOCK_BAD_REQUEST
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
def test_get_user_infos_from_access_token_success(test_authorisation):
    response = test_authorisation.get_user_infos_from_access_token(access_token=MOCK_TOKEN)
    assert response.subject == MOCK_SUB
    assert response.issuer == MOCK_ISS


@pytest.mark.parametrize("config_file", CONFIGS.values(), ids=CONFIGS.keys())
def test_get_user_infos_from_access_token_fail(test_authorisation):
    assert test_authorisation.get_user_infos_from_access_token(access_token="bad token") == None
    assert test_authorisation.get_user_infos_from_access_token(access_token=None) == None


@pytest.mark.parametrize(
    "config_file",
    CONFIGS_AUTHENTICATED_USERS.values(),
    ids=CONFIGS_AUTHENTICATED_USERS.keys(),
)
def test_get_uid_from_request_success(test_authorisation):
    response = test_authorisation.get_uid_from_request(request=MOCK_REQUEST)
    assert isinstance(response, Dict)
    assert response == {"sub": MOCK_SUB, "iss": MOCK_ISS}


@pytest.mark.parametrize("config_file", CONFIGS.values(), ids=CONFIGS.keys())
def test_get_uid_from_request_fail(test_authorisation):
    assert test_authorisation.get_uid_from_request(request=MOCK_BAD_REQUEST) == None
    assert test_authorisation.get_uid_from_request(request=None) == None

from typing import Dict
import pytest

from .utils import InfoAuthorisation, MC_REQUEST, MC_BAD_REQUEST
from .test_env import MC_ISS, MC_SUB, MC_TOKEN
from .configs import CONFIGS


async def view_func(*args, **kwargs):
    return {"message": "Success"}


configs_authenticated_users = [
    "SUPPORTED_NOT_AUTHORISED",
    "AUTHORISE_ALL",
    "INDIVIDUAL",
    "VO_BASED"
]

configs_authorised_users = [
    "AUTHORISE_ALL",
    "INDIVIDUAL",
    "VO_BASED"
]

configs_not_authorised_users = [
    "NOT_SUPPORTED",
    "SUPPORTED_NOT_AUTHORISED"
]

configs_authorised_admins = [
    "ADMIN",
    "ADMIN_FOR_ALL"
]


@pytest.mark.parametrize("config_file", [CONFIGS[c] for c in configs_authenticated_users],
    ids=configs_authenticated_users)
def test_info_authorisation(test_authorisation):
    response = test_authorisation.info(MC_REQUEST)
    assert set(InfoAuthorisation.valid_response.keys()) <= set(response.keys())


@pytest.mark.parametrize("config_file", [CONFIGS["NOT_SUPPORTED"]], ids=["NOT_SUPPORTED"])
def test_info_authorisation_not_supported(test_authorisation, test_unauthorised):
    with pytest.raises(test_unauthorised):
        test_authorisation.info(MC_REQUEST)


@pytest.mark.parametrize("config_file", [CONFIGS[c] for c in configs_authorised_users],
    ids=configs_authorised_users)
async def test_require_authorised_user_success(test_authorisation):
    assert await test_authorisation.authorised_user_required(view_func)(
        request=MC_REQUEST
    ) == {"message": "Success"}


@pytest.mark.parametrize("config_file,status_code", [
        (CONFIGS["SUPPORTED_NOT_AUTHORISED"], 403),
        (CONFIGS["NOT_SUPPORTED"], 401),
    ],
    ids=["SUPPORTED_NOT_AUTHORISED", "NOT_SUPPORTED"])
async def test_require_authorised_user_fail(test_authorisation, status_code):
    response = await test_authorisation.authorised_user_required(view_func)(request=MC_REQUEST)
    assert response.status_code == status_code


@pytest.mark.parametrize("config_file",  CONFIGS.values(), ids=CONFIGS.keys())
async def test_require_authorised_user_bad_request(test_authorisation):
    response = await test_authorisation.authorised_user_required(view_func)(request=MC_BAD_REQUEST)
    assert response.status_code == 401


@pytest.mark.parametrize("config_file,iss", [
    (CONFIGS["ADMIN"], MC_ISS),
    (CONFIGS["ADMIN_FOR_ALL"], MC_ISS),
    (CONFIGS["ADMIN_FOR_ALL"], "anything")
])
async def test_require_authorised_admin_success(test_authorisation, iss):
    assert await test_authorisation.authorised_admin_required(view_func)(
        request=MC_REQUEST, iss=iss
    ) == {"message": "Success"}


@pytest.mark.parametrize("config_file", [CONFIGS["ADMIN"]], ids=["ADMIN"])
async def test_require_authorised_admin_fail(test_authorisation):
    response = await test_authorisation.authorised_admin_required(view_func)(request=MC_REQUEST, iss="anything")
    assert response.status_code == 403


@pytest.mark.parametrize("config_file", [CONFIGS[c] for c in configs_authorised_admins],
    ids=configs_authorised_admins)
async def test_require_authorised_admin_bad_request(test_authorisation):
    response = await test_authorisation.authorised_admin_required(view_func)(request=MC_BAD_REQUEST, iss="anything")
    assert response.status_code == 401


@pytest.mark.parametrize("config_file", [CONFIGS[c] for c in configs_authenticated_users],
    ids=configs_authenticated_users)
async def test_require_authenticated_user_success(test_authorisation):
    assert await test_authorisation.authenticated_user_required(view_func)(
        request=MC_REQUEST
    ) == {"message": "Success"}


@pytest.mark.parametrize("config_file",  [CONFIGS["NOT_SUPPORTED"]], ids=["NOT_SUPPORTED"])
async def test_require_authenticated_user_fail(test_authorisation):
    response = await test_authorisation.authenticated_user_required(view_func)(request=MC_REQUEST)
    assert response.status_code == 401


@pytest.mark.parametrize("config_file",  CONFIGS.values(), ids=CONFIGS.keys())
async def test_require_authenticated_user_bad_request(test_authorisation):
    response = await test_authorisation.authenticated_user_required(view_func)(request=MC_BAD_REQUEST)
    assert response.status_code == 401


@pytest.mark.parametrize("config_file", [CONFIGS[c] for c in configs_authenticated_users],
    ids=configs_authenticated_users)
def test_get_user_infos_from_access_token_success(test_authorisation):
    response = test_authorisation.get_user_infos_from_access_token(access_token=MC_TOKEN)
    assert response.subject == MC_SUB
    assert response.issuer == MC_ISS


@pytest.mark.parametrize("config_file", CONFIGS.values(), ids=CONFIGS.keys())
def test_get_user_infos_from_access_token_fail(test_authorisation):
    assert test_authorisation.get_user_infos_from_access_token(access_token="bad token") == None
    assert test_authorisation.get_user_infos_from_access_token(access_token=None) == None


@pytest.mark.parametrize("config_file", [CONFIGS[c] for c in configs_authenticated_users],
    ids=configs_authenticated_users)
def test_get_uid_from_request_success(test_authorisation):
    response = test_authorisation.get_uid_from_request(request=MC_REQUEST)
    assert isinstance(response, Dict)
    assert response == {
        "sub": MC_SUB,
        "iss": MC_ISS
    }

@pytest.mark.parametrize("config_file", CONFIGS.values(), ids=CONFIGS.keys())
def test_get_uid_from_request_fail(test_authorisation):
    assert test_authorisation.get_uid_from_request(request=MC_BAD_REQUEST) == None
    assert test_authorisation.get_uid_from_request(request=None) == None
import pytest
import decorator
from fastapi import Request

from motley_cue.mapper.exceptions import Unauthorised

from .utils import InfoAuthorisation, MC_REQUEST
from .configs import *


@pytest.mark.parametrize("config_file", [
    CONFIG_SUPPORTED_NOT_AUTHORISED,
    CONFIG_AUTHORISE_ALL,
    CONFIG_INDIVIDUAL,
    CONFIG_VO_BASED
], ids=[
    "CONFIG_SUPPORTED_NOT_AUTHORISED",
    "CONFIG_AUTHORISE_ALL",
    "CONFIG_INDIVIDUAL",
    "CONFIG_VO_BASED"
])
def test_info_authorisation(test_authorisation):
    response = test_authorisation.info(MC_REQUEST)
    assert set(InfoAuthorisation.valid_response.keys()) <= set(response.keys())

@pytest.mark.parametrize("config_file", [CONFIG_NOT_SUPPORTED])
def test_info_authorisation_not_supported(test_authorisation):
    with pytest.raises(Unauthorised):
        test_authorisation.info(MC_REQUEST)


@pytest.mark.parametrize("config_file", [CONFIG_AUTHORISE_ALL, CONFIG_VO_BASED, CONFIG_INDIVIDUAL])
def test_require_authorised_user_success(test_authorisation):
    async def view_func(request: Request):
        _ = request
        return {"message": "Success"}
    
    assert test_authorisation.authorised_user_required(view_func)(request=MC_REQUEST) == {"message": "Success"}


@pytest.mark.parametrize("config_file", [CONFIG_NOT_SUPPORTED, CONFIG_SUPPORTED_NOT_AUTHORISED])
def test_require_authorised_user_fail(test_authorisation):
    async def view_func(request: Request):
        _ = request
        return {"message": "Success"}
    
    with pytest.raises(Unauthorised):
        test_authorisation.authorised_user_required(view_func)(request=MC_REQUEST)


@pytest.mark.parametrize("config_file", [CONFIG_ADMIN, CONFIG_ADMIN_FOR_ALL])
def test_require_authorised_admin_success(test_authorisation):
    async def view_func(request: Request, iss: str):
        _ = request
        _ = iss
        return {"message": "Success"}
    
    assert test_authorisation.authorised_admin_required(view_func)(
        request=MC_REQUEST, iss=MC_ISS
    ) == {"message": "Success"}


@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED, CONFIG_ADMIN])
def test_require_authorised_admin_fail(test_authorisation):
    async def view_func(request: Request, iss: str):
        _ = request
        _ = iss
        return {"message": "Success"}
    
    with pytest.raises(Unauthorised):
        test_authorisation.authorised_admin_required(view_func)(
            request=MC_REQUEST, iss="another iss"
        )

# test_get_userinfo_from_request
# test_get_uid_from_request
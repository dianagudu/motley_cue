from typing import Dict
import pytest

from .utils import InfoAuthorisation, MC_REQUEST, MC_BAD_REQUEST
from .test_env import MC_ISS, MC_SUB
from .configs import *


async def view_func(*args, **kwargs):
    return {"message": "Success"}


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
def test_info_authorisation_not_supported(test_authorisation, test_unauthorised):
    with pytest.raises(test_unauthorised):
        test_authorisation.info(MC_REQUEST)


@pytest.mark.parametrize("config_file", [CONFIG_AUTHORISE_ALL, CONFIG_VO_BASED, CONFIG_INDIVIDUAL])
def test_require_authorised_user_success(test_authorisation):
    assert test_authorisation.authorised_user_required(view_func)(request=MC_REQUEST) == {"message": "Success"}


@pytest.mark.parametrize("config_file", [CONFIG_NOT_SUPPORTED, CONFIG_SUPPORTED_NOT_AUTHORISED])
def test_require_authorised_user_fail(test_authorisation, test_unauthorised, test_bad_request):
    with pytest.raises(test_unauthorised):
        test_authorisation.authorised_user_required(view_func)(request=MC_REQUEST)

    with pytest.raises(test_unauthorised):
        test_authorisation.authorised_user_required(view_func)(request=MC_BAD_REQUEST)

    with pytest.raises(test_bad_request):
        test_authorisation.authorised_user_required(view_func)(request=None)

    with pytest.raises(test_bad_request):
        test_authorisation.authorised_user_required(view_func)()


@pytest.mark.parametrize("config_file", [CONFIG_ADMIN])
def test_require_authorised_admin(test_authorisation, test_unauthorised):
    assert test_authorisation.authorised_admin_required(view_func)(
        request=MC_REQUEST, iss=MC_ISS
    ) == {"message": "Success"}

    with pytest.raises(test_unauthorised):
        test_authorisation.authorised_admin_required(view_func)(request=MC_REQUEST, iss="")

    with pytest.raises(test_unauthorised):
        test_authorisation.authorised_admin_required(view_func)(request=MC_BAD_REQUEST, iss=MC_ISS)


@pytest.mark.parametrize("config_file", [CONFIG_ADMIN_FOR_ALL])
def test_require_authorised_admin_for_all(test_authorisation, test_unauthorised):
    assert test_authorisation.authorised_admin_required(view_func)(
        request=MC_REQUEST, iss=MC_ISS
    ) == {"message": "Success"}

    assert test_authorisation.authorised_admin_required(view_func)(
        request=MC_REQUEST, iss=""
    ) == {"message": "Success"}

    with pytest.raises(test_unauthorised):
        test_authorisation.authorised_admin_required(view_func)(request=MC_BAD_REQUEST, iss=MC_ISS)


@pytest.mark.parametrize("config_file", [CONFIG_ADMIN, CONFIG_ADMIN_FOR_ALL])
def test_require_authorised_admin_bad_request(test_authorisation, test_bad_request):
    with pytest.raises(test_bad_request):
        test_authorisation.authorised_admin_required(view_func)(request=MC_REQUEST, iss=None)

    with pytest.raises(test_bad_request):
        test_authorisation.authorised_admin_required(view_func)(request=MC_REQUEST)

    with pytest.raises(test_bad_request):
        test_authorisation.authorised_admin_required(view_func)(request=None, iss="")

    with pytest.raises(test_bad_request):
        test_authorisation.authorised_admin_required(view_func)(request=None)

    with pytest.raises(test_bad_request):
        test_authorisation.authorised_admin_required(view_func)()


@pytest.mark.parametrize("config_file", [CONFIG_NOT_SUPPORTED])
def test_require_authenticated_user_fail(test_authorisation, test_unauthorised, test_bad_request):
    with pytest.raises(test_unauthorised):
        test_authorisation.authenticated_user_required(view_func)(request=MC_REQUEST)

    with pytest.raises(test_unauthorised):
        test_authorisation.authenticated_user_required(view_func)(request=MC_BAD_REQUEST)

    with pytest.raises(test_bad_request):
        test_authorisation.authenticated_user_required(view_func)(request=None)

    with pytest.raises(test_bad_request):
        test_authorisation.authenticated_user_required(view_func)()



@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED, CONFIG_AUTHORISE_ALL])
def test_require_authenticated_user_success(test_authorisation):
    assert test_authorisation.authenticated_user_required(view_func)(request=MC_REQUEST) == {"message": "Success"}


@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED])
def test_get_userinfo_from_request(test_authorisation):
    assert test_authorisation.get_userinfo_from_request(request=MC_BAD_REQUEST) == None
    assert test_authorisation.get_userinfo_from_request(request=None) == None
    response = test_authorisation.get_userinfo_from_request(request=MC_REQUEST)
    assert isinstance(response, Dict)
    assert set(["sub", "iss"]).issubset(set(response.keys()))


@pytest.mark.parametrize("config_file", [CONFIG_SUPPORTED_NOT_AUTHORISED])
def test_get_uid_from_request(test_authorisation):
    assert test_authorisation.get_uid_from_request(request=MC_REQUEST) == {
        "sub": MC_SUB,
        "iss": MC_ISS
    }
    assert test_authorisation.get_uid_from_request(request=MC_BAD_REQUEST) == None
    assert test_authorisation.get_uid_from_request(request=None) == None
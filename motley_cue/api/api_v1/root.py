"""
This module contains the definition of motley_cue's REST router.
"""
from fastapi import  Depends, Request, Query, Header
from fastapi.responses import HTMLResponse

from motley_cue.api.utils import APIRouter
from motley_cue.dependencies import mapper
from motley_cue.models import Info, InfoAuthorisation, InfoOp, VerifyUser, responses
from motley_cue.api.api_v1 import user, admin

router = APIRouter()

router.include_router(user.api)
router.include_router(admin.api)


@router.get("/")
async def read_root():
    """Retrieve general API information:

    * description
    * available endpoints
    * security
    """
    return {
        "description": "This is the user API for mapping remote identities to local identities.",
        "usage": "All endpoints are available via a bearer token.",
        "endpoints": {
            f"{router.prefix}/info": "Service-specific information.",
            f"{router.prefix}/info/authorisation": (
                "Authorisation information for specific OP; "
                "requires valid access token from a supported OP."
            ),
            f"{router.prefix}/info/op": (
                "Information about a specific OP specified via a query parameter 'url'; "
                "does not require an access token."
            ),
            f"{router.prefix}/user": "User API; requires valid access token of an authorised user.",
            f"{router.prefix}/admin": (
                "Admin API; requires valid access token of an authorised user with admin role."
            ),
            f"{router.prefix}/verify_user": (
                "Verifies if a given token belongs to a given local account via 'username'."
            ),
        },
    }


@router.get("/info", response_model=Info, response_model_exclude_unset=True)
async def info():
    """Retrieve service-specific information:

    * login info
    * supported OPs
    * ops_info per OP information, such as scopes, audience, etc.
    """
    return mapper.info()


@router.get(
    "/info/authorisation",
    dependencies=[Depends(mapper.user_security)],
    response_model=InfoAuthorisation,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": InfoAuthorisation}},
)
@mapper.authenticated_user_required
async def info_authorisation(
    request: Request,
    header: str = Header(..., alias="Authorization", description="OIDC Access Token"),
):  # pylint: disable=unused-argument
    """Retrieve authorisation information for specific OP.

    Requires:

    * that the OP is supported
    * authentication with this OP
    """
    return mapper.info_authorisation(request)


@router.get(
    "/info/op",
    response_model=InfoOp,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": InfoOp}},
)
async def info_op(
    request: Request,
    url: str = Query(..., description="OP URL"),
):  # pylint: disable=unused-argument
    """Retrieve additional information for specific OP, such as required scopes.

    \f
    :param url: OP URL
    """
    return mapper.info_op(url)


@router.get(
    "/verify_user",
    dependencies=[Depends(mapper.user_security)],
    response_model=VerifyUser,
    responses={**responses, 200: {"model": VerifyUser}},
)
@mapper.inject_token
@mapper.authorised_user_required
async def verify_user(
    request: Request,
    username: str = Query(
        ...,
        description="username to compare to local username",
    ),
    header: str = Header(
        ...,
        alias="Authorization",
        description="OIDC Access Token or valid one-time token",
    ),
):  # pylint: disable=unused-argument
    """Verify that the authenticated user has a local account with the given **username**.

    Requires the user to be authorised on the service.
    \f
    :param username: username to compare to local username
    """
    return mapper.verify_user(request, username)


@router.get("/privacy", response_class=HTMLResponse)
async def privacy():
    return mapper.get_privacy_policy()


# Logo for redoc (currently disabled).
# This must be at the end after all the routes have been set!
# router.openapi()["info"]["x-logo"] = {
#     "url": "https://motley-cue.readthedocs.io/en/latest/_static/logos/motley-cue.png"
# }

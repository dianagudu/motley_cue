"""
This module contains the definition of motley_cue's REST API.
"""
from fastapi import FastAPI, Depends, Request, Query, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from .dependencies import mapper, Settings
from .routers import user, admin
from .models import Info, InfoAuthorisation, InfoOp, VerifyUser, responses, ClientError
from .mapper.exceptions import (
    validation_exception_handler,
    request_validation_exception_handler,
)

settings = Settings(docs_url=mapper.config.docs_url)
api = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    openapi_url=settings.openapi_url,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
)

api.include_router(user.api, tags=["user"])
api.include_router(admin.api, tags=["admin"])
api.add_exception_handler(RequestValidationError, request_validation_exception_handler)
api.add_exception_handler(ValidationError, validation_exception_handler)


@api.get("/")
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
            "/info": "Service-specific information.",
            "/info/authorisation": (
                "Authorisation information for specific OP; "
                "requires valid access token from a supported OP."
            ),
            "/info/op": (
                "Information about a specific OP specified via a query parameter 'url'; "
                "does not require an access token."
            ),
            "/user": "User API; requires valid access token of an authorised user.",
            "/admin": (
                "Admin API; requires valid access token of an authorised user with admin role."
            ),
            "/verify_user": (
                "Verifies if a given token belongs to a given local account via 'username'."
            ),
        },
    }


@api.get("/info", response_model=Info, response_model_exclude_unset=True)
async def info():
    """Retrieve service-specific information:

    * login info
    * supported OPs
    """
    return mapper.info()


@api.get(
    "/info/authorisation",
    dependencies=[Depends(mapper.user_security)],
    response_model=InfoAuthorisation,
    response_model_exclude_unset=True,
    responses={
        200: {"model": InfoAuthorisation},
        404: {"model": ClientError},
    },
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


@api.get(
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


@api.get(
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


@api.get("/privacy", response_class=HTMLResponse)
async def privacy():
    return mapper.get_privacy_policy()


# Logo for redoc (currently disabled).
# This must be at the end after all the routes have been set!
# api.openapi()["info"]["x-logo"] = {
#     "url": "https://motley-cue.readthedocs.io/en/latest/_static/logos/motley-cue.png"
# }

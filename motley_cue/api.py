from fastapi import FastAPI, Depends, Request, Query, Header
from fastapi.exceptions import RequestValidationError

from .dependencies import mapper, settings
from .routers import user, admin
from .models import Info, InfoAuthorisation, VerifyUser, responses
from .mapper.exceptions import validation_exception_handler


api = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    openapi_url=settings.openapi_url,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url
)

api.include_router(user.api,
                   prefix="/user",
                   tags=["user"])
api.include_router(admin.api,
                   prefix="/admin",
                   tags=["admin"])
api.add_exception_handler(RequestValidationError, validation_exception_handler)


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
            "/info/authorisation": "Authorisation information for specific OP; requires valid access token from a supported OP.",
            "/user": "User API; requires valid access token of an authorised user.",
            "/admin": "Admin API; requires valid access token of an authorised user with admin role.",
            "/verify_user": "Verifies if a given token belongs to a given local account via 'username'."
        }
    }


@api.get("/info", response_model=Info)
async def info(request: Request):
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
    responses={**responses, 200: {"model": InfoAuthorisation}}
)
@mapper.authenticated_user_required
async def info_authorisation(
        request: Request,
        token: str = Header(..., alias="Authorization", description="OIDC Access Token")
    ):
    """Retrieve authorisation information for specific OP.

    Requires:

    * that the OP is supported
    * authentication with this OP
    """
    return mapper.info_authorisation(request)


@api.get(
    "/verify_user",
    dependencies=[Depends(mapper.user_security)],
    response_model=VerifyUser,
    responses={**responses, 200: {"model": VerifyUser}}
)
@mapper.authorised_user_required
async def verify_user(
        request: Request,
        username: str = Query(..., description="username to compare to local username", ),
        token: str = Header(..., alias="Authorization", description="OIDC Access Token")
    ):
    """Verify that the authenticated user has a local account with the given **username**.

    Requires the user to be authorised on the service.
    \f
    :param username: username to compare to local username
    """
    return mapper.verify_user(request, username)


# Logo for redoc (currently disabled).
# This must be at the end after all the routes have been set!
# api.openapi()["info"]["x-logo"] = {
#     "url": "https://dianagudu.github.io/motley_cue/_static/logos/motley-cue.png"
# }
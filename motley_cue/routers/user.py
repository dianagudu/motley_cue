from fastapi import APIRouter, Request, Depends, Header

from ..dependencies import mapper
from ..models import FeudalResponse, responses


api = APIRouter()


@api.get("")
@api.get("/", include_in_schema=False)
async def read_root():
    """Retrieve user API information:

    * description
    * available endpoints
    * security
    """
    return {
        "description": "This is the user API for mapping remote identities to local identities.",
        "usage": "All endpoints are available using an OIDC Access Token as a bearer token.",
        "endpoints": {
            "/get_status": "Get information about your local account.",
            "/deploy": "Provision local account.",
            "/suspend": "Suspend local account."
        }
    }


@api.get(
    "/get_status",
    dependencies=[Depends(mapper.user_security)],
    response_model=FeudalResponse,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": FeudalResponse}}
)
@mapper.authorised_user_required
async def get_status(
        request: Request,
        token: str = Header(..., alias="Authorization", description="OIDC Access Token")
    ):
    """Get information about your local account:

    * **state**: one of the supported states, such as deployed, not_deployed, suspended.
    * **message**: could contain additional information, such as the local username

    Requires an authorised user.
    """
    return mapper.get_status(request)


@api.get(
    "/deploy",
    dependencies=[Depends(mapper.user_security)],
    response_model=FeudalResponse,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": FeudalResponse}}
)
@mapper.authorised_user_required
async def deploy(
        request: Request,
        token: str = Header(..., alias="Authorization", description="OIDC Access Token")
    ):
    """Provision a local account.

    Requires an authorised user.
    """
    return mapper.deploy(request)


@api.get(
    "/suspend",
    dependencies=[Depends(mapper.user_security)],
    response_model=FeudalResponse,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": FeudalResponse}}
)
@mapper.authorised_user_required
async def suspend(
        request: Request,
        token: str = Header(..., alias="Authorization", description="OIDC Access Token")
    ):
    """Suspends a local account.

    Requires an authorised user.
    """
    return mapper.suspend(request)

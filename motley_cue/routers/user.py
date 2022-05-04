"""
This module contains the definition of motley_cue's user API.
"""
from fastapi import APIRouter, Request, Depends, Header

from ..dependencies import mapper
from ..models import FeudalResponse, OTPResponse, responses


api = APIRouter(prefix="/user")


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
            f"{api.prefix}/get_status": "Get information about your local account.",
            f"{api.prefix}/deploy": "Provision local account.",
            f"{api.prefix}/suspend": "Suspend local account.",
            f"{api.prefix}/generate_otp": "Generates a one-time token for given access token.",
        },
    }


@api.get(
    "/get_status",
    dependencies=[Depends(mapper.user_security)],
    response_model=FeudalResponse,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": FeudalResponse}},
)
@mapper.authorised_user_required
async def get_status(
    request: Request,
    header: str = Header(..., alias="Authorization", description="OIDC Access Token"),
):  # pylint: disable=unused-argument
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
    responses={**responses, 200: {"model": FeudalResponse}},
)
@mapper.authorised_user_required
async def deploy(
    request: Request,
    header: str = Header(..., alias="Authorization", description="OIDC Access Token"),
):  # pylint: disable=unused-argument
    """Provision a local account.

    Requires an authorised user.
    """
    return mapper.deploy(request)


@api.get(
    "/suspend",
    dependencies=[Depends(mapper.user_security)],
    response_model=FeudalResponse,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": FeudalResponse}},
)
@mapper.authorised_user_required
async def suspend(
    request: Request,
    header: str = Header(..., alias="Authorization", description="OIDC Access Token"),
):  # pylint: disable=unused-argument
    """Suspends a local account.

    Requires an authorised user.
    """
    return mapper.suspend(request)


@api.get(
    "/generate_otp",
    dependencies=[Depends(mapper.user_security)],
    response_model=OTPResponse,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": OTPResponse}},
)
@mapper.authorised_user_required
async def generate_otp(
    request: Request,
    header: str = Header(..., alias="Authorization", description="OIDC Access Token"),
):  # pylint: disable=unused-argument
    """Generates and stores a new one-time password, using token as shared secret.

    Requires an authorised user.
    """
    return mapper.generate_otp(request)

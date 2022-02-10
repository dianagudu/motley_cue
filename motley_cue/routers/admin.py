from fastapi import APIRouter, Request, Depends, Query, Header

from ..dependencies import mapper
from ..models import FeudalResponse, responses


api = APIRouter()


@api.get("")
@api.get("/", include_in_schema=False)
async def read_root():
    """Retrieve admin API information:

    * description
    * available endpoints
    * security
    """
    return {
        "description": "This is the admin API for mapping remote identities to local identities.",
        "usage": "All endpoints are available using an OIDC Access Token as a bearer token and need subject and issuer of account to be modified, via 'sub' and 'iss' variables.",
        "endpoints": {
            "/suspend": "Suspends a local account.",
            "/resume": "Restores a suspended local account."
        }
    }


@api.get(
    "/suspend",
    dependencies=[Depends(mapper.user_security)],
    response_model=FeudalResponse,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": FeudalResponse}}
)
@mapper.authorised_admin_required
async def suspend(
        request: Request,
        token: str = Header(..., alias="Authorization", description="OIDC Access Token"),
        sub: str = Query(..., description="sub claim of the user to be suspended", ),
        iss: str = Query(..., description="OIDC provider of user to be suspended", )
    ):
    """Suspends a local account mapped to given OIDC account -- uniquely
    identified by issuer and subject claims.

    Requires a user with admin rights.
    \f
    :param sub: sub claim of the user to be suspended
    :param iss: OIDC provider of user to be suspended
    """
    return mapper.admin_suspend(sub, iss)


@api.get(
    "/resume",
    dependencies=[Depends(mapper.user_security)],
    response_model=FeudalResponse,
    response_model_exclude_unset=True,
    responses={**responses, 200: {"model": FeudalResponse}}
)
@mapper.authorised_admin_required
async def resume(
        request: Request,
        token: str = Header(..., alias="Authorization", description="OIDC Access Token"),
        sub: str = Query(..., description="sub claim of the user to be suspended", ),
        iss: str = Query(..., description="OIDC provider of user to be suspended", )
    ):
    """Resumes a suspended local account mapped to given OIDC account -- uniquely
    identified by issuer and subject claims.

    Requires a user with admin rights.
    \f
    :param sub: sub claim of the user to be resumed
    :param iss: OIDC provider of user to be resumed
    """
    return mapper.admin_resume(sub, iss)

from fastapi import APIRouter, Request, Depends

from ..dependencies import mapper


api = APIRouter()


@api.get("")
@api.get("/")
async def read_root(request: Request):
    return {
        "description": "This is the user API for mapping remote identities to local identities.",
        "usage": "All endpoints are available using an OIDC Access Token as a bearer token.",
        "endpoints": {
            "/get_status": "Get information about your local account.",
            "/deploy": "Provision local account.",
            "/suspend": "Suspend local account."
        }
    }


@api.get("/get_status", dependencies=[Depends(mapper.user_security)])
@mapper.authorised_user_required
async def get_status(request: Request):
    return mapper.get_status(request)


@api.get("/deploy", dependencies=[Depends(mapper.user_security)])
@mapper.authorised_user_required
async def deploy(request: Request):
    return mapper.deploy(request)


@api.get("/suspend", dependencies=[Depends(mapper.user_security)])
@mapper.authorised_user_required
async def suspend(request: Request):
    return mapper.suspend(request)

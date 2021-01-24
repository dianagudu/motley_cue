from fastapi import APIRouter, Request

from ..mapper import mapper, AdminActions


api = APIRouter()


@api.get("/")
@mapper.authorised_admin_required()
async def read_root(request: Request):
    return {
        "description": "This is the admin API for mapping remote identities to local identities.",
        "usage": "All endpoints are available using a bearer token and need subject and issuer of account to be modified, via 'sub' and 'iss' variables.",
        "endpoints": {
            "/undeploy": "Deprovision a local account.",
            "/suspend": "Suspends a local account.",
            "/resume": "Restores a suspended local account.",
            "/expire": "Takes a local account into an 'expired' state with limited capabilities."
        }
    }


@api.get("/undeploy")
@mapper.authorised_admin_required()
async def undeploy(request: Request, sub: str, iss: str):
    return mapper.admin_action(sub, iss, AdminActions.undeploy)


@api.get("/suspend")
@mapper.authorised_admin_required()
async def suspend(request: Request, sub: str, iss: str):
    return mapper.admin_action(sub, iss, AdminActions.suspend)


@api.get("/resume")
@mapper.authorised_admin_required()
async def resume(request: Request, sub: str, iss: str):
    return mapper.admin_action(sub, iss, AdminActions.resume)


@api.get("/expire")
@mapper.authorised_admin_required()
async def expire(request: Request, sub: str, iss: str):
    return mapper.admin_action(sub, iss, AdminActions.expire)

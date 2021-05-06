from fastapi import APIRouter, Request, Depends

from ..dependencies import mapper


api = APIRouter()


@api.get("")
@api.get("/")
async def read_root(request: Request):
    return {
        "description": "This is the admin API for mapping remote identities to local identities.",
        "usage": "All endpoints are available using an OIDC Access Token as a bearer token and need subject and issuer of account to be modified, via 'sub' and 'iss' variables.",
        "endpoints": {
            "/suspend": "Suspends a local account.",
            "/resume": "Restores a suspended local account."
        }
    }


@api.get("/suspend", dependencies=[Depends(mapper.user_security)])
@mapper.authorised_admin_required
async def suspend(request: Request, sub: str, iss: str):
    return mapper.admin_suspend(sub, iss)


@api.get("/resume", dependencies=[Depends(mapper.user_security)])
@mapper.authorised_admin_required
async def resume(request: Request, sub: str, iss: str):
    return mapper.admin_resume(sub, iss)

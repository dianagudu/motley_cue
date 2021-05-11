from fastapi import FastAPI, Depends, Request
from .dependencies import mapper
from .routers import user, admin


api = FastAPI()

api.include_router(user.api,
                   prefix="/user",
                   tags=["user"])
api.include_router(admin.api,
                   prefix="/admin",
                   tags=["admin"])


@api.get("/")
async def read_root():
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


@api.get("/info")
async def info(request: Request):
    return mapper.info()


@api.get("/info/authorisation", dependencies=[Depends(mapper.user_security)])
@mapper.login_required()
async def info_authorisation(request: Request):
    return mapper.info_authorisation(request)


@api.get("/verify_user", dependencies=[Depends(mapper.user_security)])
@mapper.authorised_user_required
async def verify_user(request: Request, username: str):
    return mapper.verify_user(request, username)

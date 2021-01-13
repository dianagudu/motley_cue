from fastapi import FastAPI, Depends, Request
from .mapper import mapper
from .user import user
from .admin import admin


api = FastAPI()

api.include_router(user.api,
                   prefix="/user",
                   tags=["user"],
                   dependencies=[Depends(mapper.user_security)])
api.include_router(admin.api,
                   prefix="/admin",
                   tags=["admin"],
                   dependencies=[Depends(mapper.admin_security)])


@api.get("/")
async def read_root():
    return {
        "description": "This is the user API for mapping remote identities to local identities.",
        "usage": "All endpoints are available via a bearer token.",
        "endpoints": {
            "/info": "Service-specific information.",
            "/user": "User API; requires valid access token of an authorised user.",
            "/admin": "Admin API; requires valid access token of an authorised user with admin role.",
            "/verify_user": "Verifies if a given token belongs to a given local account via 'username'."
        }
    }


@api.get('/info', dependencies=[Depends(mapper.user_security)])
@mapper.login_required()
async def info(request: Request):
    return mapper.info()


@api.get('/verify_user')
@mapper.authorized_login_required()
async def verify_user(request: Request, username: str):
    return mapper.verify_user(request, username)

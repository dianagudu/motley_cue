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
    text = '''This is an API for mapping remote identities to local identities.
    These endpoints are available:
    /info           Service-specific information
    /user           User API; requires valid access token of an authorized user
    /admin          Admin API; available via admin credentials
    /verify_user    Verifies if a given token belongs to a given local username
    '''
    return {"info": text}


@api.get('/info')
async def info():
    return mapper.info()


@api.get('/verify_user')
@mapper.authorized_login_required()
async def verify_user(request: Request, username: str):
    return mapper.verify_user(request, username)

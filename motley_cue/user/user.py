from fastapi import APIRouter, Request

from ..mapper import mapper, States


api = APIRouter()


@api.get("/")
@mapper.authorized_login_required()
async def read_root(request: Request):
    text = '''This is the user API for mapping remote identities to local identities.
    These endpoints are available using a bearer token:
    /get        Get information about your local account.
    /deploy     Provision local account.
    /undeploy   Deprovision local account.
    '''
    return {"info": text}


@api.get("/get")
@mapper.authorized_login_required()
async def get(request: Request):
    return mapper.get(request)


@api.get("/deploy")
@mapper.authorized_login_required()
async def deploy(request: Request):
    return mapper.reach_state(request, States.deployed)


@api.get("/undeploy")
@mapper.authorized_login_required()
async def undeploy(request: Request):
    return mapper.reach_state(request, States.not_deployed)

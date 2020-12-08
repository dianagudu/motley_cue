from fastapi import APIRouter, Request

from ..mapper import mapper


api = APIRouter()


@api.get("/")
@mapper.authorized_login_required()
async def read_root(request: Request):
    text = '''This is the admin API for mapping remote identities to local identities.
    These endpoints are available using a bearer token:
    /undeploy   Deprovision a local account.
    /authorise  Accepts a pending deployment request from a user and finalizes the local account provisioning.
    /suspend    Suspends a local account.
    /resume     Restores a suspended local account.
    /expire     Takes a local account into an “expired” state with limited capabilities.
    '''
    return {"info": text}

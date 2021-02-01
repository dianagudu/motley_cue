from fastapi import APIRouter, Request

from ..mapper import mapper, States


api = APIRouter()


@api.get("/")
@mapper.authorised_user_required()
async def read_root(request: Request):
    return {
        "description": "This is the user API for mapping remote identities to local identities.",
        "usage": "All endpoints are available using a bearer token.",
        "endpoints": {
            "/get_status": "Get information about your local account.",
            "/deploy": "Provision local account.",
            "/suspend": "Suspend local account."
        }
    }


@api.get("/get_status")
@mapper.authorised_user_required()
async def get_status(request: Request):
    return mapper.reach_state(request, States.get_status)


@api.get("/deploy")
@mapper.authorised_user_required()
async def deploy(request: Request):
    return mapper.reach_state(request, States.deployed)


@api.get("/suspend")
@mapper.authorised_user_required()
async def suspend(request: Request):
    return mapper.reach_state(request, States.suspended)

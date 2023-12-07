from motley_cue.api.utils import APIRouter
from motley_cue.api.api_v1 import root


api_router = APIRouter()
api_router.include_router(root.router)
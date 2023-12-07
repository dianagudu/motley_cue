from motley_cue.api.utils import APIRouter
from motley_cue.api.api_v1 import endpoints


api_router = APIRouter()
api_router.include_router(endpoints.router)

from motley_cue.apis.utils import APIRouter
from motley_cue.apis.v1 import root, user, admin


router = APIRouter()
router.include_router(root.router)
router.include_router(user.router)
router.include_router(admin.router)

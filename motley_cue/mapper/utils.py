from fastapi.responses import JSONResponse


class MapperResponse(JSONResponse):
    def __init__(self, content, status_code=200):
        super().__init__(content, status_code)

# store here the exact URL for some OPs as found in an AT issued by them
# e.g. some have a trailing slash, but flaat strips that off
EXACT_OP_URLS = [
    'https://wlcg.cloud.cnaf.infn.it/',
    'https://aai.egi.eu/oidc/',
]

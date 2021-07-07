from fastapi.responses import JSONResponse

class MapperResponse(JSONResponse):
    def __init__(self, content, status_code=200):
        super().__init__(content, status_code)
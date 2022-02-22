from typing import Callable, List, Dict
from fastapi import Request
from starlette.datastructures import Headers

from .test_env import MC_TOKEN


class Endpoint():
    def __init__(
            self, url: str, valid_response: Dict,
            children: List = [], params: List = [],
            mapper_method: str = "",
            protected: bool = False):
        self.url = url
        self.children = children
        self.params = params
        self.protected = protected
        self.mapper_method = mapper_method
        self.valid_response = valid_response
        self.callback_valid = lambda *x: valid_response


Info = Endpoint(
    url="/info",
    valid_response={"login_info": "", "supported_OPs": []},
    mapper_method="info"
)

InfoAuthorisation = Endpoint(
    url="/info/authorisation",
    valid_response={"OP": "", "authorisation_type": "", "authorisation_info": ""},
    mapper_method="info_authorisation",
    protected=True
)

VerifyUser = Endpoint(
    url="/verify_user",
    valid_response={"state": "", "verified": False},
    params=["username"],
    mapper_method="verify_user",
    protected=True
)

User = Endpoint(
    url="/user",
    valid_response={"description": "", "endpoints": {}, "usage": ""},
    children=[
        Endpoint(child_url, valid_response=child_resp, mapper_method=child_mapper_method, protected=True)
        for child_url, child_resp, child_mapper_method in [
            ("/user/deploy", {"state": "", "message": "", "credentials": {}}, "deploy"),
            ("/user/get_status", {"state": "", "message": ""}, "get_status"),
            ("/user/suspend", {"state": "", "message": ""}, "suspend")
        ]
    ]
)

Admin = Endpoint(
    url="/admin",
    valid_response={"description": "", "endpoints": {}, "usage": ""},
    children=[
        Endpoint(
            url=child_url, valid_response=child_resp,
            params=["iss", "sub"], mapper_method=child_mapper_method, protected=True
        ) for child_url, child_resp, child_mapper_method in [
            ("/admin/suspend", {"state": "", "message": ""}, "admin_suspend"),
            ("/admin/resume", {"state": "", "message": ""}, "admin_resume")
        ]
    ]
)

Root = Endpoint(
    url="/",
    valid_response={"description": "", "endpoints": {}, "usage": ""},
    children=[Info, InfoAuthorisation, User, Admin, VerifyUser]
)


def getListOfEndpoints(endpoint: Endpoint, condition: Callable[[Endpoint], bool]) -> List[Endpoint]:
    endpoints = []
    if condition(endpoint):
        endpoints += [endpoint]
    if endpoint.children:
        for child in endpoint.children:
            endpoints += getListOfEndpoints(child, condition)
    return endpoints


PUBLIC_ENDPOINTS = getListOfEndpoints(Root, condition=lambda x: not x.protected)
PROTECTED_ENDPOINTS = getListOfEndpoints(Root, condition=lambda x: x.protected)
QUERY_ENDPOINTS = getListOfEndpoints(Root, condition=lambda x: len(x.params)>0)


def build_query_string(params: Dict = {}) -> str:
    return "&".join(["=".join(x) for x in params.items()])


def build_request(token: str = None, params: Dict = {}) -> Request:
    if token is None:
        headers = {}
    else:
        headers = Headers({"Authorization": f"Bearer {token}"}).raw
    return Request({
        "type": "http",
        "headers": headers,
        "path": "/"
        # "query_string": bytes(build_query_string(params), "utf-8"),
    })


MC_HEADERS = {"Authorization": f"Bearer {MC_TOKEN}"}
MC_REQUEST = build_request(MC_TOKEN)
import os


class Endpoint():
    def __init__(self, endpoint, keys=None, children=None, protected=False):
        self.endpoint = endpoint
        self.keys = keys
        self.children = children
        self.protected = protected


Info = Endpoint(
    endpoint="/info",
    keys=["login info", "supported OPs"]
)

InfoAuthorisation = Endpoint(
    endpoint="/info/authorisation",
    keys=["OP", "description", "info"],
    protected=True
)

VerifyUser = Endpoint(
    endpoint="/verify_user",
    keys=["status", "verified"],
    protected=True
)

User = Endpoint(
    endpoint="/user",
    keys=["description", "endpoints", "usage"],
    children=[
        Endpoint(child_url, child_keys, protected=True)
        for child_url, child_keys in [
            ("/user/deploy", None),
            ("/user/get_status", ["state", "message"]),
            ("/user/suspend", ["state", "message"])
        ]
    ]
)

Admin = Endpoint(
    endpoint="/admin",
    keys=["description", "endpoints", "usage"],
    children=[
        Endpoint(child_url, child_keys, protected=True)
        for child_url, child_keys in [
            ("/admin/suspend", ["state", "message"]),
            ("/admin/resume", ["state", "message"])
        ]
    ]
)

Root = Endpoint(
    endpoint="/",
    keys=["description", "endpoints", "usage"],
    children=[Info, InfoAuthorisation, User, Admin, VerifyUser]
)


def getListOfEndpoints(endpoint, protected=False):
    endpoints = []
    if endpoint.protected == protected:
        endpoints += [endpoint]
    if endpoint.children:
        for child in endpoint.children:
            endpoints += getListOfEndpoints(child, protected)
    return endpoints


PUBLIC_ENDPOINTS = getListOfEndpoints(Root, False)
PROTECTED_ENDPOINTS = getListOfEndpoints(Root, True)

TOKEN = {
    "BADTOKEN": "BADTOKEN",
    "NOT_SUPPORTED": os.getenv("KIT_TOKEN"),
    "SUPPORTED_NOT_AUTHORISED": os.getenv("DEEP_TOKEN"),
    "AUTHORISE_ALL": os.getenv("WLCG_TOKEN"),
    "INDIVIDUAL": os.getenv("EGI_TOKEN"),
    "VO_BASED": os.getenv("HELMHOLTZ_DEV_TOKEN")
}

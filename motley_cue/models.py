from typing import Optional
from pydantic import BaseModel, Field

from .mapper.utils import AuthorisationType


class Info(BaseModel):
    login_info: dict = Field(..., example={
        "description": "Local SSH Test Service",
        "login_help": "Login via `mccli ssh {login_host}`.",
        "ssh_host": "localhost"
    })
    supported_OPs: list = Field(..., example=[
        "https://aai.egi.eu/oidc",
        "https://login.helmholtz.de/oauth2"
    ])


class InfoAuthorisation(BaseModel):
    OP: str = Field (..., example="https://wlcg.cloud.cnaf.infn.it/")
    authorisation_type: str = Field(..., example=AuthorisationType.vo_based.description()["authorisation_type"])
    authorisation_info: str = Field (..., example=AuthorisationType.vo_based.description()["authorisation_info"])
    supported_VOs: Optional[list] = Field ([], example=["/wlcg"])


class VerifyUser(BaseModel):
    state: str = Field (..., example="deployed")
    verified: bool = Field (..., example=True)


class FeudalResponse(BaseModel):
    state: str = Field (..., example="deployed")
    message: str = Field (..., example="User was created and was added to groups wlcg.")
    credentials: Optional[dict] = Field ({}, example={
        "commandline": "ssh wlcg001@localhost",
        "description": "Local SSH Test Service",
        "login_help": "Login via `mccli ssh {login_host}`.",
        "ssh_host": "localhost",
        "ssh_user": "wlcg001"
    })


class ClientError(BaseModel):
    detail: str


responses = {
    400: {"model": ClientError},
    401: {"model": ClientError},
    403: {"model": ClientError},
}

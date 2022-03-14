"""Definitions of API response models
"""
from typing import Optional, Union, List
from pydantic.dataclasses import dataclass
from pydantic import Field

from .mapper.authorisation import AuthorisationType


@dataclass
class Info:
    """Data model for responses on the /info endpoint."""

    login_info: dict = Field(
        ...,
        example={
            "description": "Local SSH Test Service",
            "login_help": "Login via `mccli ssh {login_host}`.",
            "ssh_host": "localhost",
        },
    )
    supported_OPs: list = Field(  # pylint: disable=invalid-name
        ...,
        example=[
            "https://aai.egi.eu/oidc",
            "https://login.helmholtz.de/oauth2",
        ],
    )


@dataclass
class InfoAuthorisation:
    """Data model for responses on the /info/authorisation endpoint."""

    OP: str = Field(  # pylint: disable=invalid-name
        ..., example="https://wlcg.cloud.cnaf.infn.it/"
    )
    authorisation_type: str = Field(
        ..., example=AuthorisationType.VO_BASED.description()["authorisation_type"]
    )
    authorisation_info: str = Field(
        ..., example=AuthorisationType.VO_BASED.description()["authorisation_info"]
    )
    supported_VOs: Optional[list] = Field(  # pylint: disable=invalid-name
        [], example=["/wlcg"]
    )
    audience: Optional[Union[str, List[str]]] = Field("", example="ssh_localhost")


@dataclass
class VerifyUser:
    """Data model for responses on the /verify_user endpoint."""

    state: str = Field(..., example="deployed")
    verified: bool = Field(..., example=True)


@dataclass
class FeudalResponse:
    """Data model for any responses coming from FeudalAdapter,
    on any /user/* and /admin/* endpoints.
    """

    state: str = Field(..., example="deployed")
    message: str = Field(..., example="User was created and was added to groups wlcg.")
    credentials: Optional[dict] = Field(
        {},
        example={
            "commandline": "ssh wlcg001@localhost",
            "description": "Local SSH Test Service",
            "login_help": "Login via `mccli ssh {login_host}`.",
            "ssh_host": "localhost",
            "ssh_user": "wlcg001",
        },
    )


@dataclass
class ClientError:
    """Data model for responses on errors."""

    detail: str


@dataclass
class FlaatError:
    """Data model for responses on errors coming from FLAAT"""

    error: str
    error_description: str
    error_details: Optional[str]


responses = {
    401: {"model": Union[ClientError, FlaatError]},
    403: {"model": Union[ClientError, FlaatError]},
    404: {"model": Union[ClientError, FlaatError]},
}

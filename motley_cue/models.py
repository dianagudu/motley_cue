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

    OP: str = Field(..., example="https://wlcg.cloud.cnaf.infn.it/")  # pylint: disable=invalid-name
    authorisation_type: str = Field(
        ..., example=AuthorisationType.VO_BASED.description()["authorisation_type"]
    )
    authorisation_info: str = Field(
        ..., example=AuthorisationType.VO_BASED.description()["authorisation_info"]
    )
    supported_VOs: Optional[list] = Field([], example=["/wlcg"])  # pylint: disable=invalid-name
    audience: Optional[Union[str, List[str]]] = Field("", example="ssh_localhost")


@dataclass
class InfoOp:
    """Data model for responses on the /info/op endpoint."""

    scopes: Optional[List[str]] = Field([], example=["openid", "profile", "email"])
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
class OTPResponse:
    """Data model for any responses coming from TokenManager,
    on /user/generate_otp.
    Information on whether OTPs are supported, in which case also
    whether the OTP generation and storage succeeded.
    """

    supported: bool = Field(..., example=True)
    successful: bool = Field(False, example=True)
    # message: Optional[str] = Field("", example="OTPs not supported.")


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

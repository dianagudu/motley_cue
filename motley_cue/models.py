"""Definitions of API response models
"""
from typing import Optional, Union, List, Dict
from pydantic.dataclasses import dataclass
from pydantic import Field

from .mapper.authorisation import AuthorisationType


@dataclass
class InfoOp:
    """Data model for responses on the /info/op endpoint."""

    scopes: Optional[List[str]] = Field([], examples=[["openid", "profile", "email"]])
    audience: Optional[Union[str, List[str]]] = Field("", examples=["ssh_localhost"])


@dataclass
class Info:
    """Data model for responses on the /info endpoint."""

    login_info: dict = Field(
        ...,
        examples=[
            {
                "description": "Local SSH Test Service",
                "login_help": "Login via `mccli ssh {login_host}`.",
                "ssh_host": "localhost",
            }
        ],
    )
    supported_OPs: list = Field(  # pylint: disable=invalid-name
        ...,
        examples=[
            [
                "https://aai.egi.eu/oidc",
                "https://login.helmholtz.de/oauth2",
            ]
        ],
    )
    ops_info: Dict[str, InfoOp] = Field(
        {},
        examples=[
            {
                "https://aai.egi.eu/oidc": {
                    "scopes": ["openid", "profile", "email"],
                    "audience": "ssh_localhost",
                },
                "https://login.helmholtz.de/oauth2": {
                    "scopes": ["openid", "profile", "email"],
                    "audience": "ssh_localhost",
                },
            }
        ],
    )


@dataclass
class InfoAuthorisation:
    """Data model for responses on the /info/authorisation endpoint."""

    OP: str = Field(
        ..., examples=["https://wlcg.cloud.cnaf.infn.it/"]
    )  # pylint: disable=invalid-name
    authorisation_type: str = Field(
        ..., examples=[AuthorisationType.VO_BASED.description()["authorisation_type"]]
    )
    authorisation_info: str = Field(
        ..., examples=[AuthorisationType.VO_BASED.description()["authorisation_info"]]
    )
    supported_VOs: Optional[list] = Field(
        [], examples=[["/wlcg"]]
    )  # pylint: disable=invalid-name
    audience: Optional[Union[str, List[str]]] = Field("", examples=["ssh_localhost"])


@dataclass
class VerifyUser:
    """Data model for responses on the /verify_user endpoint."""

    state: str = Field(..., examples=["deployed"])
    verified: bool = Field(..., examples=[True])


@dataclass
class FeudalResponse:
    """Data model for any responses coming from FeudalAdapter,
    on any /user/* and /admin/* endpoints.
    """

    state: str = Field(..., examples=["deployed"])
    message: str = Field(
        ..., examples=["User was created and was added to groups wlcg."]
    )
    credentials: Optional[dict] = Field(
        {},
        examples=[
            {
                "commandline": "ssh wlcg001@localhost",
                "description": "Local SSH Test Service",
                "login_help": "Login via `mccli ssh {login_host}`.",
                "ssh_host": "localhost",
                "ssh_user": "wlcg001",
            }
        ],
    )


@dataclass
class OTPResponse:
    """Data model for any responses coming from TokenManager,
    on /user/generate_otp.
    Information on whether OTPs are supported, in which case also
    whether the OTP generation and storage succeeded.
    """

    supported: bool = Field(..., examples=[True])
    successful: bool = Field(False, examples=[True])
    # message: Optional[str] = Field("", examples=["OTPs not supported.")


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

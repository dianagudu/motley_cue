"""Map OIDC remote identity to local account"""
# This code is distributed under the MIT License

import sys
import logging
import logging.handlers
from fastapi import Request
from fastapi.security import HTTPBearer
from fastapi.responses import HTMLResponse

from .config import Config
from .authorisation import Authorisation
from .local_user_management import LocalUserManager
from .exceptions import Unauthorised, NotFound
from .token_manager import TokenManager
from ..static import md_to_html


class Mapper:
    """Mapping component that deals with authN & authZ,
    as well as interfacing with the local user management
    """

    def __init__(self, config: Config):
        self.__config = config
        # configure logging
        if self.__config.log_file is None or self.__config.log_file == "/dev/stderr":
            log_handler = logging.StreamHandler()
        elif self.__config.log_file == "/dev/stdout":
            log_handler = logging.StreamHandler(sys.stdout)
        else:
            try:
                log_handler = logging.handlers.RotatingFileHandler(
                    self.__config.log_file, maxBytes=100**6, backupCount=2
                )
            except Exception:  # pylint: disable=broad-except
                # anything goes wrong, fallback to stderr
                log_handler = logging.StreamHandler()
        log_format = "[%(asctime)s] [%(name)s] %(levelname)s - %(message)s"
        logging.basicConfig(
            level=self.__config.log_level,
            handlers=[log_handler],
            format=log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        self.__user_security = HTTPBearer(description="OIDC Access Token")
        self.__admin_security = HTTPBearer(description="OIDC Access Token")
        self.__authorisation = Authorisation(self.__config)
        self.__lum = LocalUserManager()
        self.__token_manager = TokenManager.from_config(self.__config.otp)

    @property
    def authorisation(self):
        """Authorisation object"""
        return self.__authorisation

    @property
    def config(self):
        """Config object"""
        return self.__config

    @property
    def user_security(self):
        """User security for FastAPI"""
        return self.__user_security

    @property
    def admin_security(self):
        """Admin security for FastAPI"""
        return self.__admin_security

    def info(self):
        """Return information about the local service:
        * supported OPs
        * login information
        """
        return {
            "login_info": self.__lum.login_info(),
            "supported_OPs": self.__authorisation.trusted_op_list,
        }

    def info_op(self, url: str):
        """Return information about a given OP"""
        info = self.__config.get_op_info(url)
        if info is None:
            raise NotFound(message="OP not supported")
        return info

    def info_authorisation(self, request):
        """Return authorisation information for issuer of token.
        OIDC Access Token should be found in request headers.
        """
        return self.__authorisation.info(request)

    def authenticated_user_required(self, func):
        """Decorator that only allows users from supported OPs.
        OIDC Access Token should be found in request headers.
        """
        return self.__authorisation.authenticated_user_required(func)

    def authorised_user_required(self, func):
        """Decorator that only allows users from supported OPs that meet the
        configured authorisation requirements.
        OIDC Access Token should be found in request headers.
        """
        return self.__authorisation.authorised_user_required(func)

    def authorised_admin_required(self, func):
        """Decorator that only allows admins from supported OPs that meet the
        configured authorisation requirements.
        OIDC Access Token should be found in request headers.
        """
        return self.__authorisation.authorised_admin_required(func)

    def inject_token(self, func):
        """Decorator that replaces the given token (OTP) with its corresponding AT.
        Only if OTPs are supported, and if given token is found in OTP db.
        Otherwise pass token through as is, and it will be treated like an AT.
        """
        if not self.__token_manager:
            return func
        return self.__token_manager.inject_token(func)

    def deploy(self, request: Request):
        """Deploy a local account for user identified by token.
        OIDC Access Token should be found in request headers.
        """
        user_infos = self.__authorisation.get_user_infos_from_request(request)
        if user_infos is None:
            raise Unauthorised(message="No user infos")
        return self.__lum.deploy(user_infos.user_info)

    def get_status(self, request: Request):
        """Get the status of a local account corresponding to the user identified by token.
        OIDC Access Token should be found in request headers.
        """
        userinfo = self.__authorisation.get_uid_from_request(request)
        return self.__lum.get_status(userinfo)

    def suspend(self, request: Request):
        """Suspend a local account corresponding to the user identified by token.
        OIDC Access Token should be found in request headers.
        """
        userinfo = self.__authorisation.get_uid_from_request(request)
        return self.__lum.suspend(userinfo)

    def generate_otp(self, request: Request):
        """Generates and stores a one-time password from token.
        Returns whether operation was successful.
        """
        if not self.__token_manager:
            return {"supported": False}
        return self.__token_manager.generate_otp(
            self.__authorisation._get_access_token_from_request(request)
        )

    def admin_suspend(self, sub: str, iss: str):
        """Suspend a local account corresponding to the user identified by
        OIDC sub and iss claims.
        """
        return self.__lum.admin_suspend(sub, iss)

    def admin_resume(self, sub: str, iss: str):
        """Resume a suspended local account corresponding to the user identified by
        OIDC sub and iss claims.
        """
        return self.__lum.admin_resume(sub, iss)

    def verify_user(self, request: Request, username: str):
        """Verify that the local account corresponding to the user identified by token
        has the given username.
        OIDC Access Token should be found in request headers.
        """
        userinfo = self.__authorisation.get_uid_from_request(request)
        return self.__lum.verify_user(userinfo, username)

    def get_privacy_policy(self):
        """Retrieve the privacy policy as html.

        Returns dict with fields:
        * content: html content containing the privacy policy
        * status_code: HTTP status code
        """
        try:
            html = md_to_html(
                mdfile=self.config.privacy.privacy_file,
                title="motley-cue privacy policy",
            )
            html = html.replace("{{privacy_contact}}", self.config.privacy.privacy_contact)
            return HTMLResponse(content=html, status_code=200)
        except FileNotFoundError as e:
            logging.getLogger(__name__).error("Privacy policy file not found: %s", e)
            return HTMLResponse(content="Privacy policy not found", status_code=404)
        except Exception as e:
            logging.getLogger(__name__).error("Error retrieving privacy policy: %s", e)
            return HTMLResponse(content=f"Error retrieving privacy policy", status_code=500)

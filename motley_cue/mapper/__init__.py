'''Map OIDC remote identity to local account'''
# This code is distributed under the MIT License

import sys
import logging
import logging.handlers
from fastapi import Request
from fastapi.security import HTTPBearer

from .config import Config
from .authorisation import Authorisation
from .local_user_management import LocalUserManager


class Mapper:
    """Mapping component that deals with authN & authZ,
    as well as interfacing with the local user management
    """

    def __init__(self, config_file=None):
        if config_file is None:
            self.__config = Config.from_default_files()
        else:
            self.__config = Config.from_files([config_file])

        # configure logging
        if self.__config.log_file is None or \
                self.__config.log_file == "/dev/stderr":
            log_handler = logging.StreamHandler()
        elif self.__config.log_file == "/dev/stdout":
            log_handler = logging.StreamHandler(sys.stdout)
        else:
            try:
                log_handler = logging.handlers.RotatingFileHandler(
                    self.__config.log_file, maxBytes=100**6, backupCount=2)
            except Exception:
                # anything goes wrong, fallback to stderr
                log_handler = logging.StreamHandler()
        log_format = "[%(asctime)s] [%(name)s] %(levelname)s - %(message)s"
        logging.basicConfig(level=self.__config.log_level,
                            handlers=[log_handler],
                            format=log_format,
                            datefmt='%Y-%m-%d %H:%M:%S')

        self.__user_security = HTTPBearer(description="OIDC Access Token")
        self.__admin_security = HTTPBearer(description="OIDC Access Token")
        self.__authorisation = Authorisation(self.__config)
        self.__lum = LocalUserManager()

    @property
    def config(self):
        return self.__config

    @property
    def user_security(self):
        return self.__user_security

    @property
    def admin_security(self):
        return self.__admin_security

    def info(self):
        # here we return service name, description, supported OPs
        return {
            "login_info": self.__lum.login_info(),
            "supported_OPs": self.__authorisation.trusted_op_list,
        }

    def info_authorisation(self, request):
        return self.__authorisation.info(request)

    def authenticated_user_required(self, func):
        return self.__authorisation.authenticated_user_required(func)

    def authorised_user_required(self, func):
        return self.__authorisation.authorised_user_required(func)

    def authorised_admin_required(self, func):
        return self.__authorisation.authorised_admin_required(func)

    def deploy(self, request: Request):
        userinfo = self.__authorisation.get_userinfo_from_request(request)
        return self.__lum.deploy(userinfo)

    def get_status(self, request: Request):
        userinfo = self.__authorisation.get_uid_from_request(request)
        return self.__lum.get_status(userinfo)

    def suspend(self, request: Request):
        userinfo = self.__authorisation.get_uid_from_request(request)
        return self.__lum.suspend(userinfo)

    def admin_suspend(self, sub: str, iss: str):
        return self.__lum.admin_suspend(sub, iss)

    def admin_resume(self, sub: str, iss: str):
        return self.__lum.admin_resume(sub, iss)

    def verify_user(self, request: Request, username: str):
        userinfo = self.__authorisation.get_uid_from_request(request)
        return self.__lum.verify_user(userinfo, username)

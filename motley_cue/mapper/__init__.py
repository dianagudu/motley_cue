'''Map OIDC remote identity to local account'''
# This code is distributed under the MIT License

from fastapi import Request
from fastapi.security import HTTPBearer

from .. import logger as parent_logger
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
        # log setup for parent module to be inherited by child modules
        parent_logger.setLevel(self.__config.log_level)
        self.__user_security = HTTPBearer()
        self.__admin_security = HTTPBearer()
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
            "login info": self.__lum.login_info(),
            "supported OPs": self.__authorisation.trusted_op_list,
        }

    def info_authorisation(self, request):
        return self.__authorisation.info(request)

    def login_required(self):
        return self.__authorisation.login_required()

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
        state = "unknown"
        try:
            result = self.get_status(request)
            state = result['state']
            local_username = result['message'].split()[1]
        except Exception:
            local_username = None
        return {
            "state": state,
            "verified": (local_username == username)
        }

'''Map OIDC remote identity to local account'''
# This code is distributed under the MIT License
# pylint
# vim: tw=100 foldmethod=indent
# pylint: disable=bad-continuation, invalid-name, superfluous-parens
# pylint: disable=bad-whitespace

import logging
from enum import Enum
from flaat import Flaat, tokentools
from ldf_adapter import User
from ldf_adapter.results import ExceptionalResult
from fastapi import Request
from fastapi.security import HTTPBearer
from .config import CONFIG, to_list, to_bool


logger = logging.getLogger(__name__)


class States(Enum):
    deployed = 0,
    not_deployed = 1,
    pending = 2,
    suspended = 3,
    expired = 4,
    failed = 5,
    get_status = 6


class Mapper:
    """Mapping component that deals with authN & authZ,
    as well as interfacing with the local user management
    """

    def __init__(self):
        self.__user_security = HTTPBearer()
        self.__admin_security = HTTPBearer()
        self.__flaat = FlaatWrapper()
        self.__lum = LUM()

    @property
    def user_security(self):
        return self.__user_security

    @property
    def admin_security(self):
        return self.__admin_security

    def info(self):
        # here we can return service name, description,
        # supported IdPs, supported VOs, ...
        return {"info": "SSH"}

    def login_required(self):
        return self.__flaat.login_required()

    def authorized_login_required(self):
        return self.__flaat.authorized_login_required()

    def authorised_admin_required(self):
        return self.__flaat.authorised_admin_required()

    def deploy(self, request: Request):
        return self.__lum.reach_state(
            self.__flaat.userinfo_from_request(request),
            States.deployed
        )

    def reach_state(self, request: Request, state_target: States):
        return self.__lum.reach_state(
            self.__flaat.uid_from_request(request),
            state_target
        )

    def reach_state_with_uid(self, sub: str, iss: str, state_target: States):
        return self.__lum.reach_state(
            {
                "sub": sub,
                "iss": iss
            },
            state_target
        )

    def verify_user(self, request: Request, username: str):
        result = self.reach_state(request, States.get_status)
        try:
            local_username = result['message'].split()[1]
        except Exception:
            local_username = None
        return {
            "state": result['state'],
            "verified": (local_username == username)
        }


class FlaatWrapper(Flaat):
    """
    FLAAT configured with given parameters in config file
    """

    def __init__(self):
        super().__init__()
        super().set_web_framework("fastapi")
        super().set_cache_lifetime(120)  # seconds; default is 300
        super().set_trusted_OP_list(
            to_list(CONFIG['mapper.flaat']['trusted_OP_list']))
        try:
            verbosity = int(CONFIG['mapper.flaat']['verbosity'])
            super().set_verbosity(verbosity
                                  if verbosity >= 0 and verbosity <= 3
                                  else 0)
        except Exception:
            super().set_verbosity(0)
            logger.warning("Verbosity not set or invalid, defaults to 0.")
        try:
            super().set_client_id(CONFIG['mapper.flaat']['client_id'])
            super().set_client_secret(CONFIG['mapper.flaat']['client_secret'])
        except Exception:
            logger.warning(
                "No OIDC client credentials, introspection endpoint cannot be used.")

        try:
            self.__authorise_all = to_bool(
                CONFIG['mapper.flaat.authorisation']['authorise_all'])
        except Exception:
            self.__authorise_all = False

        try:
            authorisation_info = CONFIG['mapper.flaat.authorisation']
            # parse match option, defaults to all when missing
            try:
                match = authorisation_info['match']
                match = match if match == 'all' or match == 'one' else int(
                    match)
            except Exception:
                match = 'all'
            # parse aarc_g002_option, defaults to False when missing
            try:
                aarc_g002_group = to_bool(
                    authorisation_info['aarc_g002_group'])
            except Exception:
                aarc_g002_group = False
            self.__authorisation_info = {
                'group': to_list(authorisation_info['group']),
                'claim': authorisation_info['claim'],
                'match': match,
                'aarc_g002_group': aarc_g002_group
            }
        except Exception:
            self.__authorisation_info = None
            logger.warning(
                "Missing or invalid authorisation information in config file, defaults to blocking all users.")

    def authorized_login_required(self):
        if self.__authorise_all:
            return self.login_required()
        if self.__authorisation_info is None:
            return self._return_formatter_wf("No authorisation info in config file", 401)
        return self.is_authorised()

    def authorised_admin_required(self):
        # FIXME
        return self.login_required()

    def is_authorised(self):
        if self.__authorisation_info['aarc_g002_group']:
            return self.aarc_g002_group_required(
                group=self.__authorisation_info['group'],
                claim=self.__authorisation_info['claim'],
                match=self.__authorisation_info['match']
            )
        else:
            return self.group_required(
                group=self.__authorisation_info['group'],
                claim=self.__authorisation_info['claim'],
                match=self.__authorisation_info['match']
            )

    def userinfo_from_request(self, request: Request):
        token = tokentools.get_access_token_from_request(request)
        userinfo = self.get_info_from_userinfo_endpoints(token)
        # add issuer to userinfo  -> needed by feudalAdapter
        userinfo["iss"] = tokentools.get_issuer_from_accesstoken_info(token)
        return userinfo

    def uid_from_request(self, request: Request):
        token = tokentools.get_access_token_from_request(request)
        # try to get it from access token (token already validated and user authorised)
        try:
            token_info = tokentools.get_accesstoken_info(token)
            return {
                "sub": token_info['body']['sub'],
                "iss": token_info['body']['iss']
            }
        except Exception:
            # go to user endpoint
            userinfo = self.get_info_from_userinfo_endpoints(token)
            return {
                "sub": userinfo['sub'],
                "iss": tokentools.get_issuer_from_accesstoken_info(token)
            }


class LUM:
    def __init__(self):
        pass

    def reach_state(self, userinfo, state_target: States):
        data = {
            "state_target": state_target.name,
            "user": {
                "userinfo": userinfo,
            },
        }

        logger.debug(f"Attempting to reach state '{data['state_target']}'")

        if data['user']['userinfo'] is None:
            logger.error("Cannot process null input")
            return None

        try:
            result = User(data).reach_state(data['state_target'])
        except ExceptionalResult as result:
            result = result.attributes
            logger.debug("Reached state '{state}': {message}".format(**result))
            return result
        else:
            result = result.attributes
            logger.debug("Reached state '{state}': {message}".format(**result))
            return result


mapper = Mapper()

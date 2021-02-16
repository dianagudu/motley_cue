'''Map OIDC remote identity to local account'''
# This code is distributed under the MIT License
# pylint
# vim: tw=100 foldmethod=indent
# pylint: disable=bad-continuation, invalid-name, superfluous-parens
# pylint: disable=bad-whitespace

import logging
from enum import Enum
from flaat import Flaat, tokentools
from fastapi import Request
from fastapi.security import HTTPBearer
from .config import CONFIG, to_list, to_bool

from feudal_globalconfig import globalconfig
globalconfig.config['parse_commandline_args'] = False
from ldf_adapter import User
from ldf_adapter.results import ExceptionalResult

logger = logging.getLogger(__name__)


class States(Enum):
    deployed = 0,
    not_deployed = 1,
    pending = 2,
    suspended = 3,
    limited = 4,
    unknown = 5,
    get_status = 6


class AdminActions(Enum):
    suspend = 0,
    resume = 1,
    undeploy = 2


class Mapper:
    """Mapping component that deals with authN & authZ,
    as well as interfacing with the local user management
    """

    def __init__(self):
        self.__user_security = HTTPBearer()
        self.__admin_security = HTTPBearer()
        self.__flaat = FlaatWrapper()

    @property
    def user_security(self):
        return self.__user_security

    @property
    def admin_security(self):
        return self.__admin_security

    def info(self):
        # here we can return service name, description,
        # supported IdPs, supported VOs, ...
        try:
            login_info = CONFIG['backend.{}.login_info'
                                .format(CONFIG['ldf_adapter']['backend'])]
        except Exception:
            login_info = {}
        return {
            "login info": login_info,
            "supported IdPs": self.__flaat.trusted_op_list,
            "authorisation": self.__flaat.str_repr_user_authorisation
        }

    def login_required(self):
        return self.__flaat.login_required()

    def authorised_user_required(self):
        return self.__flaat.authorised_user_required()

    def authorised_admin_required(self):
        return self.__flaat.authorised_admin_required()

    def reach_state(self, request: Request, state_target: States):
        if state_target == States.deployed:
            userinfo = self.__flaat.userinfo_from_request(request)
        else:
            userinfo = self.__flaat.uid_from_request(request)
        if userinfo is None:
            logger.error("Cannot process null input")
            return None
        # build input for feudalAdapter
        data = {
            "state_target": state_target.name,
            "user": {
                "userinfo": userinfo,
            },
        }
        try:
            logger.debug(f"Attempting to reach state '{state_target.name}'")
            result = User(data).reach_state(data['state_target'])
        except ExceptionalResult as result:
            result = result.attributes
            logger.debug("Reached state '{state}': {message}".format(**result))
            return result
        else:
            result = result.attributes
            logger.debug("Reached state '{state}': {message}".format(**result))
            return result

    def admin_action(self, sub: str, iss: str, action: AdminActions):
        data = {
            "user": {
                "userinfo": {
                    "sub": sub,
                    "iss": iss
                }
            }
        }
        try:
            if action == AdminActions.suspend:
                result = User(data).reach_state(States.suspended.name)
            elif action == AdminActions.resume:
                result = User(data).resume()
            elif action == AdminActions.undeploy:
                result = User(data).reach_state(States.not_deployed.name)
        except ExceptionalResult as result:
            result = result.attributes
            logger.debug("Reached state '{state}': {message}".format(**result))
            return result
        else:
            result = result.attributes
            logger.debug("Reached state '{state}': {message}".format(**result))
            return result

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

        self.__user_authorisation = self.__read_authorisation_info(
            'mapper.flaat.authorisation')
        self.__admin_authorisation = self.__read_authorisation_info(
            'mapper.flaat.admin')

    @property
    def str_repr_user_authorisation(self):
        return self.__authorisation_str_repr(self.__user_authorisation)

    @property
    def str_repr_admin_authorisation(self):
        return self.__authorisation_str_repr(self.__admin_authorisation)

    @staticmethod
    def __read_authorisation_info(config_section):
        try:
            authorise_all = to_bool(
                CONFIG[config_section]['authorise_all'])
        except Exception:
            authorise_all = False

        try:
            authorisation_info = CONFIG[config_section]
            # parse match option, defaults to all when missing
            match = authorisation_info.get('match', 'all')
            match = match if match == 'all' or match == 'one' else int(match)
            # parse aarc_g002_option, defaults to False when missing
            aarc_g002_group = to_bool(authorisation_info.get('aarc_g002_group', False))
            info = {
                'group': to_list(authorisation_info['group']),  # required
                'claim': authorisation_info['claim'],  # required
                'match': match,
                'aarc_g002_group': aarc_g002_group
            }
        except Exception:
            info = None
            logger.warning(
                "Missing or invalid authorisation information in config file, defaults to blocking all users.")

        return {
            'authorise_all': authorise_all,
            'info': info
        }

    @staticmethod
    def __authorisation_str_repr(authorisation):
        try:
            if authorisation['authorise_all']:
                return {"info": "all users from supported IdPs are authorised"}
            elif authorisation['info'] is None:
                return {"info": "no one is authorised"}
            else:
                return {
                    "info": "user must be in " +
                            str(authorisation['info']['match']) +
                            " of the supported VOs",
                    "supported VOs": authorisation['info']['group']
                }
        except Exception:
            return {"info": "invalid authorisation => no one is authorised"}

    def authorised_user_required(self):
        return self.is_authorised(self.__user_authorisation)

    def authorised_admin_required(self):
        return self.is_authorised(self.__admin_authorisation)

    def is_authorised(self, authorisation):
        if authorisation['authorise_all']:
            return self.login_required()
        if authorisation['info'] is None:
            return self._return_formatter_wf("No authorisation info in config file", 401)
        if authorisation['info']['aarc_g002_group']:
            return self.aarc_g002_group_required(
                group=authorisation['info']['group'],
                claim=authorisation['info']['claim'],
                match=authorisation['info']['match']
            )
        else:
            return self.group_required(
                group=authorisation['info']['group'],
                claim=authorisation['info']['claim'],
                match=authorisation['info']['match']
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


mapper = Mapper()

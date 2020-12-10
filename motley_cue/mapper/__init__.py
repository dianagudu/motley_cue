'''Map OIDC remote identity to local account'''
# This code is distributed under the MIT License
# pylint
# vim: tw=100 foldmethod=indent
# pylint: disable=bad-continuation, invalid-name, superfluous-parens
# pylint: disable=bad-whitespace

import logging
from enum import Enum
from flaat import Flaat
from ldf_adapter import User
from ldf_adapter.results import ExceptionalResult
from fastapi import Request
from fastapi.security import HTTPBearer
from .config import CONFIG, to_list, to_bool

if CONFIG['mapper']['db'] == 'file':
    import json
    import pathlib
elif CONFIG['mapper']['db'] == 'redis':
    import redis

logger = logging.getLogger(__name__)


class States(Enum):
    deployed = 0,
    not_deployed = 1,
    pending = 2,
    suspended = 3,
    expired = 4,
    failed = 5


class Mapper:
    """Mapping component that deals with authN & authZ,
    as well as interfacing with the local user management
    """

    def __init__(self):
        self.__user_security = HTTPBearer()
        self.__admin_security = HTTPBearer()
        self.__flaat = FlaatWrapper()
        self.__lum = LUM()
        self.__db = RedisMapperDB(**CONFIG['mapper.redis'])\
            if CONFIG['mapper']['db'] == 'redis' \
            else FileMapperDB(CONFIG['mapper.file']['location'])

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

    def authorized_login_required(self):
        return self.__flaat.authorized_login_required()

    def get(self, request: Request):
        local_username = self.__db.get(
            self.__flaat.uid_from_request(request)
        )
        # FIXME: get actual state
        if local_username is None:
            return {
                "state": "not_deployed"
            }
        else:
            return {
                "username": local_username,
                "state": "deployed"
            }

    def reach_state(self, request: Request, state_target: States):
        result = self.__lum.reach_state(
            self.__flaat.userinfo_from_request(request),
            state_target
        )
        logger.info(result)
        unique_id = self.__flaat.uid_from_request(request)
        if state_target == States.deployed and result['state'] == 'deployed':
            local_username = result['credentials']['ssh_user']
            logger.info(
                f"Adding mapping for remote id {unique_id} to local id {local_username}")
            self.__db.add(unique_id, local_username)
        elif state_target == States.not_deployed and result['state'] == 'not_deployed':
            logger.info(f"Removing local user {self.__db.get(unique_id)}")
            self.__db.remove(unique_id)
        else:
            pass
        return result

    def verify_user(self, request: Request, username: str):
        local_username = self.__db.get(
            self.__flaat.uid_from_request(request)
        )
        # FIXME: get actual state
        if local_username is None:
            return {
                "verified": False,
                "state": "not_deployed"
            }
        else:
            verified = (local_username == username)
            return {
                "verified": verified,
                "state": "deployed"
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
        userinfo = self._get_all_info_from_request(request)
        # FIX: iss not present in info from user endpoint
        userinfo["iss"] = userinfo["body"]["iss"]
        return userinfo

    def uid_from_request(self, request: Request):
        userinfo = self._get_all_info_from_request(request)
        iss = userinfo["body"]["iss"]
        sub = userinfo["body"]["sub"]
        return iss+sub


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


# Simple Redis DB to store all mappings from remote to local identity
class MapperDB:
    def __init__(self):
        pass

    def get(self, unique_id):
        return None

    def add(self, unique_id, local_username):
        pass

    def remove(self, unique_id):
        pass


class FileMapperDB(MapperDB):
    def __init__(self, filename):
        super().__init__()
        self.__filename = filename

    def read_mappings(self):
        if pathlib.Path(self.__filename).exists():
            with open(self.__filename) as file:
                mappings = json.load(file)
        else:
            mappings = {}
        return mappings

    def write_mappings(self, mappings):
        with open(self.__filename, "w+") as file:
            json.dump(mappings, file)

    def get(self, unique_id):
        try:
            mappings = self.read_mappings()
            return mappings[unique_id]
        except Exception:
            logger.warning(f"No mapping found for {unique_id}.")
            return None

    def add(self, unique_id, local_username):
        try:
            # these operations have to be atomic
            mappings = self.read_mappings()
            mappings[unique_id] = local_username
            self.write_mappings(mappings)
        except Exception:
            logger.warning(
                f"Something wentwrong when adding mapping {unique_id} to {local_username}.")

    def remove(self, unique_id):
        try:
            # these operations have to be atomic
            mappings = self.read_mappings()
            del mappings[unique_id]
            self.write_mappings(mappings)
        except Exception:
            logger.warning(
                f"No mapping found for {unique_id}, cannot be removed.")


class RedisMapperDB(MapperDB):
    def __init__(self, endpoint='localhost', db=0, port=6379, password=''):
        super().__init__()
        self.__mappings = redis.StrictRedis(
            host=endpoint,
            db=db,
            port=port,
            password=password,
            decode_responses=True)

    def get(self, unique_id):
        return self.__mappings.get(unique_id)

    def add(self, unique_id, local_username):
        self.__mappings.set(unique_id, local_username)

    def remove(self, unique_id):
        self.__mappings.delete(unique_id)


mapper = Mapper()

import logging
from enum import Enum

from feudal_globalconfig import globalconfig
globalconfig.config['parse_commandline_args'] = False
from ldf_adapter.config import CONFIG as LDF_ADAPTER_CONFIG
from ldf_adapter.results import ExceptionalResult
from ldf_adapter import User


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


class LocalUserManager():
    def __init__(self):
        # might be a good idea to add config params here,
        # e.g. feudal config if the adapter would support it
        # or supported states, etc...
        pass

    def deploy(self, userinfo):
        return self._reach_state(userinfo, States.deployed)

    def get_status(self, userinfo):
        return self._reach_state(userinfo, States.get_status)

    def suspend(self, userinfo):
        return self._reach_state(userinfo, States.suspended)

    def admin_suspend(self, sub: str, iss: str):
        return self._admin_action(sub, iss, AdminActions.suspend)

    def admin_resume(self, sub: str, iss: str):
        return self._admin_action(sub, iss, AdminActions.resume)

    def login_info(self):
        try:
            login_info = LDF_ADAPTER_CONFIG[
                'backend.{}.login_info'
                .format(LDF_ADAPTER_CONFIG['ldf_adapter']['backend'])]
        except Exception:
            login_info = {}
        return login_info

    def _reach_state(self, userinfo, state_target: States):
        if userinfo is None:
            logging.getLogger(__name__).error("Cannot process null input")
            return None
        # build input for feudalAdapter
        data = {
            "state_target": state_target.name,
            "user": {
                "userinfo": userinfo,
            },
        }
        try:
            logging.getLogger(__name__).debug(
                f"Attempting to reach state '{state_target.name}'")
            result = User(data).reach_state(data['state_target'])
        except ExceptionalResult as result:
            result = result.attributes
            logging.getLogger(__name__).debug(
                "Reached state '{state}': {message}".format(**result))
            return result
        else:
            result = result.attributes
            logging.getLogger(__name__).debug(
                "Reached state '{state}': {message}".format(**result))
            return result

    def _admin_action(self, sub: str, iss: str, action: AdminActions):
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
            logging.getLogger(__name__).debug(
                "Reached state '{state}': {message}".format(**result))
            return result
        else:
            result = result.attributes
            logging.getLogger(__name__).debug(
                "Reached state '{state}': {message}".format(**result))
            return result

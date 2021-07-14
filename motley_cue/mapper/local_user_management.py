import logging
from enum import Enum

from feudal_globalconfig import globalconfig
globalconfig.config['parse_commandline_args'] = False
from ldf_adapter.config import CONFIG as LDF_ADAPTER_CONFIG
from ldf_adapter.results import ExceptionalResult, Rejection
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
            login_info = dict(
                    LDF_ADAPTER_CONFIG[
                        'backend.{}.login_info'
                        .format(LDF_ADAPTER_CONFIG['ldf_adapter']['backend'])
                ])
        except Exception:
            login_info = {}
        return login_info

    def verify_user(self, userinfo, username):
        state = "unknown"
        local_username = None
        try:
            logging.getLogger(__name__).info(
                f"Attempting to verify if local username for userinfo {userinfo} is '{username}'")
            result = self.get_status(userinfo)
            if result["status_code"] == 200:
                state = result["content"]["state"]
                if state != States.not_deployed.name and state != States.unknown.name:
                    local_username = result["content"]["message"].split()[1]
        except Exception:
            logging.getLogger(__name__).warning(f"Could not verify token for username {username}: {e}")
        return {
            "state": state,
            "verified": (local_username == username)
        }

    def _reach_state(self, userinfo, state_target: States):
        if userinfo is None:
            logging.getLogger(__name__).error("Something went wrong when trying to get userinfo for feudal.")
            return {
                "content": {
                    "state": States.unknown.name,
                    "message": "Something went wrong when trying to retrieve user info."
                },
                "status_code": 500
            }
        # build input for feudalAdapter
        data = {
            "state_target": state_target.name,
            "user": {
                "userinfo": userinfo,
            },
        }
        try:
            result = User(data).reach_state(data['state_target'])
        except ExceptionalResult as result:
            if isinstance(result, Rejection):
                status_code = 403  # forbidden
            else:
                status_code = 500  # internal server error
            result = result.attributes
            logging.getLogger(__name__).warning(
                "Reached state '{state}': {message}".format(**result))
            return {
                "content": result,
                "status_code": status_code
            }
        else:
            result = result.attributes
            logging.getLogger(__name__).info(
                "Reached state '{state}': {message}".format(**result))
            return {
                "content": result,
                "status_code": 200
            }

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
            logging.getLogger(__name__).info(
                f"Attempting to perform admin action '{action.name}' on user: [sub: {sub}, iss: {iss}]"
            )
            if action == AdminActions.suspend:
                result = User(data).reach_state(States.suspended.name)
            elif action == AdminActions.resume:
                result = User(data).resume()
            elif action == AdminActions.undeploy:
                result = User(data).reach_state(States.not_deployed.name)
        except ExceptionalResult as result:
            if isinstance(result, Rejection):
                status_code = 403  # forbidden
            else:
                status_code = 500  # internal server error
            result = result.attributes
            logging.getLogger(__name__).warning(
                "Reached state '{state}': {message}".format(**result))
            return {
                "content": result,
                "status_code": status_code
            }
        else:
            result = result.attributes
            logging.getLogger(__name__).info(
                "Reached state '{state}': {message}".format(**result))
            return {
                "content": result,
                "status_code": 200
            }

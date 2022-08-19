"""Module for interfacing with local user management, i.e. FeudalAdapter.
"""
import logging
from enum import Enum

# pylint: disable=wrong-import-position
from feudal_globalconfig import globalconfig

globalconfig.config["parse_commandline_args"] = False
from ldf_adapter.config import CONFIG as LDF_ADAPTER_CONFIG
from ldf_adapter.results import ExceptionalResult, Rejection
from ldf_adapter import User

from .exceptions import Unauthorised, InternalServerError


class States(Enum):
    """Possible states for local accounts"""

    # pylint: disable=invalid-name
    # for compatibility with feudal state names
    deployed = 0
    not_deployed = 1
    pending = 2
    suspended = 3
    limited = 4
    unknown = 5
    get_status = 6


class AdminActions(Enum):
    """Possible actions for admins on local accounts"""

    SUSPEND = 0
    RESUME = 1
    UNDEPLOY = 2


class LocalUserManager:
    """Interface to local user management"""

    # pylint: disable=no-self-use
    # for future configurable LUM
    def __init__(self):
        """Creates local user management object."""
        # might be a good idea to add config params here,
        # e.g. feudal config if the adapter would support it
        # or supported states, etc...

    def deploy(self, userinfo):
        """Deploys a local account for given userinfo"""
        return self._reach_state(userinfo, States.deployed)

    def get_status(self, userinfo):
        """Gets the status of the local account corresponding given userinfo"""
        return self._reach_state(userinfo, States.get_status)

    def suspend(self, userinfo):
        """Suspends the local account corresponding given userinfo"""
        return self._reach_state(userinfo, States.suspended)

    def admin_suspend(self, sub: str, iss: str):
        """Suspends the local account of a user given by its OIDC sub and iss"""
        return self._admin_action(sub, iss, AdminActions.SUSPEND)

    def admin_resume(self, sub: str, iss: str):
        """Resumes a suspended local account of a user given by its OIDC sub and iss"""
        return self._admin_action(sub, iss, AdminActions.RESUME)

    def login_info(self):
        """Returns a dict containing the login information for the configured feudal backend."""
        try:
            login_info = LDF_ADAPTER_CONFIG.login_info.to_dict()
        except Exception:  # pylint: disable=broad-except
            login_info = {}
        return login_info

    def verify_user(self, userinfo, username: str):
        """Verifies that the local username corresponding to the OIDC user given by userinfo
        is the same as the given username.
        The result of this comparison is in the "verified" field of the returned dict.
        The returned dict also contains the state of the local account in "state".
        """
        state = "unknown"
        local_username = None
        try:
            logging.getLogger(__name__).info(
                "Attempting to verify if local username for userinfo %s is '%s'",
                userinfo,
                username,
            )
            result = self.get_status(userinfo)
            state = result["state"]
            if state not in [States.not_deployed.name, States.unknown.name]:
                local_username = result["message"].split()[1]
        except Exception as ex:
            logging.getLogger(__name__).warning(
                "Could not verify token for username %s: %s", username, ex
            )
            raise InternalServerError("Something went wrong.") from ex
        return {
            "state": state,
            "verified": (local_username == username and username is not None),
        }

    def _reach_state(self, userinfo, state_target: States):
        """Interface with the Feudal Adapter s.t. the local account of the OIDC user
        given by userinfo is put into the state "state_target".
        """
        if userinfo is None:
            logging.getLogger(__name__).error(
                "Something went wrong when trying to get userinfo for feudal."
            )
            raise InternalServerError("Something went wrong when trying to retrieve user info.")
        # build input for feudalAdapter
        data = {
            "state_target": state_target.name,
            "user": {
                "userinfo": userinfo,
            },
        }
        try:
            result = User(data).reach_state(data["state_target"])
        except ExceptionalResult as result:
            msg = f"Reached state '{result.attributes['state']}': {result.attributes['message']}"
            logging.getLogger(__name__).warning(msg)
            if isinstance(result, Rejection):
                raise Unauthorised(msg) from result
            raise InternalServerError(msg) from result
        except Exception as ex:
            logging.getLogger(__name__).warning(ex)
            raise InternalServerError(
                f"Something went wrong when trying to reach state {data['state_target']}"
            ) from ex
        else:
            result = result.attributes
            logging.getLogger(__name__).info(
                "Reached state '%s': %s", result["state"], result["message"]
            )
            return result

    def _admin_action(self, sub: str, iss: str, action: AdminActions):
        """Interfaces with the Feudal Adapter s.t. the given admin action is applied
        to the local account of the OIDC user given by sub and iss.
        """
        data = {"user": {"userinfo": {"sub": sub, "iss": iss}}}
        try:
            logging.getLogger(__name__).info(
                "Attempting to perform admin action '%s' on user: [sub: %s, iss: %s]",
                action.name,
                sub,
                iss,
            )
            if action == AdminActions.SUSPEND:
                result = User(data).reach_state(States.suspended.name)
            elif action == AdminActions.RESUME:
                result = User(data).resume()
            elif action == AdminActions.UNDEPLOY:
                result = User(data).reach_state(States.not_deployed.name)
        except ExceptionalResult as result:
            msg = f"Reached state '{result.attributes['state']}': {result.attributes['message']}"
            logging.getLogger(__name__).warning(msg)
            if isinstance(result, Rejection):
                raise Unauthorised(msg) from result
            raise InternalServerError(msg) from result
        except Exception as ex:
            raise InternalServerError(
                f"Something went wrong with admin action {action.name}."
            ) from ex
        else:
            result = result.attributes
            logging.getLogger(__name__).info(
                "Reached state '%s': %s", result["state"], result["message"]
            )
            return result

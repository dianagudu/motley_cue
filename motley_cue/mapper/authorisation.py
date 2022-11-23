"""
Authorisation module for motley_cue API.
"""
from typing import Optional
from enum import Enum
import logging

from fastapi import Request
from flaat import AuthWorkflow
from flaat.config import AccessLevel
from flaat.fastapi import Flaat
from flaat.requirements import CheckResult, Requirement
from flaat.user_infos import UserInfos
from flaat.exceptions import FlaatException

from .config import Config, ConfigAuthorisation, canonical_url
from .exceptions import Unauthorised


logger = logging.getLogger(__name__)

# We dynamically load the requirement in is_satisfied_by
class AuthRequirement(Requirement):
    """Base class for authorisation requirements corresponding to an OP."""

    # pylint: disable=too-few-public-methods
    def __init__(self, authorisation: ConfigAuthorisation):
        self.authorisation = authorisation


class AuthenticatedUserRequirement(AuthRequirement):
    """Requirement for a user to be able to login at the OP."""

    # pylint: disable=too-few-public-methods
    def is_satisfied_by(self, user_infos: UserInfos) -> CheckResult:
        """override method to use configured authorisation"""
        op_authz = self.authorisation.get_op_authz(user_infos)
        if op_authz is None:
            return CheckResult(False, "OP is not configured")

        return CheckResult(True, "OP is configured")


class AuthorisedUserRequirement(AuthRequirement):
    """Requirement for a user to meet the configured authorisation for the OP."""

    # pylint: disable=too-few-public-methods
    def is_satisfied_by(self, user_infos: UserInfos) -> CheckResult:
        """override method to use configured authorisation"""
        op_authz = self.authorisation.get_op_authz(user_infos)
        if op_authz is None:
            return CheckResult(False, "OP is not configured")

        return op_authz.get_user_requirement().is_satisfied_by(user_infos)


class AuthorisedAdminRequirement(AuthRequirement):
    """Requirement for an admin to meet the configured authorisation for the OP."""

    # pylint: disable=too-few-public-methods
    def is_satisfied_by(self, user_infos: UserInfos) -> CheckResult:
        """override method to use configured authorisation"""
        op_authz = self.authorisation.get_op_authz(user_infos)
        if op_authz is None:
            return CheckResult(False, "OP is not configured")

        return op_authz.get_admin_requirement().is_satisfied_by(user_infos)


class AuthorisationType(Enum):
    """Class to describe authorisation for an OP."""

    NOT_SUPPORTED = ("not supported", "OP is not supported.")
    NOT_CONFIGURED = (
        "not configured",
        "OP is supported but no authorisation is configured.",
    )
    ALL_USERS = ("all users", "All users from this OP are authorised.")
    INDIVIDUAL_USERS = (
        "individual users",
        "Users are authorised on an individual basis. "
        "Please contact a service administrator to request access.",
    )
    VO_BASED = ("VO-based", "Users who are in {} of the supported VOs are authorised")

    def __init__(self, mode, info):
        """Create authorisation type"""
        self.__mode = mode
        self.__info = info

    def description(self, vo_match="one", audience=""):
        """Return a description of the authorisation as a dict"""
        desc_dict = {
            "authorisation_type": self.__mode,
            "authorisation_info": self.__info.format(vo_match),
        }
        if audience is not None and audience != "" and audience != []:
            desc_dict["audience"] = audience
        return desc_dict


class Authorisation(Flaat):
    """Extension for Flaat:

    - configures Flaat parameters in given config file
    - more flexible authorisation:
        - per OP configuration
        - individual user authorisation
    - stringify authorisation info
    """

    def __init__(self, config: Config):
        """Initialise Authorisation from given Config object"""
        super().__init__()
        self.set_trusted_OP_list(config.trusted_ops)
        self.set_verbosity(config.verbosity)
        self.__authorisation = config.authorisation
        self.access_levels = [
            AccessLevel("authenticated_user", AuthenticatedUserRequirement(self.__authorisation)),
            AccessLevel("authorised_user", AuthorisedUserRequirement(self.__authorisation)),
            AccessLevel("authorised_admin", AuthorisedAdminRequirement(self.__authorisation)),
        ]

    def info(self, request: Request) -> dict:
        """Return authorisation information for issuer of token.
        OIDC Access Token should be found in request headers.
        """
        # get OP from request
        try:
            user_infos = self.get_user_infos_from_request(request)
        except FlaatException as ex:
            logger.info("Error while trying to get user infos from request: %s", ex)
            user_infos = None
        if user_infos is None:
            raise Unauthorised("Could not get user infos from request.")
        op_authz = self.__authorisation.get_op_authz(user_infos)
        # if OP not supported
        if op_authz is None:
            return {
                "OP": user_infos.issuer,
                **AuthorisationType.NOT_SUPPORTED.description(),
            }
        # if all users from this OP are authorised
        if op_authz.authorise_all:
            return {
                "OP": op_authz.op_url,
                **AuthorisationType.ALL_USERS.description(audience=op_authz.audience),
            }
        # if authorised VOs are specified
        if len(op_authz.authorised_vos) > 0:
            return {
                "OP": op_authz.op_url,
                **AuthorisationType.VO_BASED.description(
                    vo_match=op_authz.vo_match, audience=op_authz.audience
                ),
                "supported_VOs": op_authz.authorised_vos,
            }
        # if individual users are specified
        if len(op_authz.authorised_users) > 0:
            return {
                "OP": op_authz.op_url,
                **AuthorisationType.INDIVIDUAL_USERS.description(audience=op_authz.audience),
            }

        # OP is supported but no authorisation is configured
        return {
            "OP": op_authz.op_url,
            **AuthorisationType.NOT_CONFIGURED.description(audience=op_authz.audience),
        }

    def authenticated_user_required(self, func):
        """Decorator that only allows users from supported OPs.
        OIDC Access Token should be found in request headers.
        """
        return self.access_level("authenticated_user")(func)

    def authorised_user_required(self, func):
        """Decorator that only allows users from supported OPs that meet the
        configured authorisation requirements.
        OIDC Access Token should be found in request headers.
        """
        return self.access_level("authorised_user")(func)

    def authorised_admin_required(self, func):
        """Decorator that only allows admins from supported OPs that meet the
        configured authorisation requirements.
        OIDC Access Token should be found in request headers.
        """

        def _check_request(user_infos: UserInfos, *_, **kwargs) -> CheckResult:
            user_iss = kwargs.get("iss", "")
            if user_iss != "":
                op_authz = self.__authorisation.get_op_authz(user_infos)
                if op_authz is None:
                    return CheckResult(False, "No OP config")

                if not op_authz.authorise_admins_for_all_ops and canonical_url(
                    op_authz.op_url
                ) != canonical_url(user_iss):
                    return CheckResult(
                        False,
                        f"Admin from issuer {op_authz.op_url} is not authorised to manage "
                        f"users of issuer '{user_iss}'",
                    )

            return CheckResult(True, "Request is authorised")

        auth_flow = AuthWorkflow(
            self,
            user_requirements=self._get_access_level_requirement("authorised_admin"),
            request_requirements=_check_request,
        )
        return auth_flow.decorate_view_func(func)

    def get_user_infos_from_access_token(self, access_token, issuer_hint="") -> Optional[UserInfos]:
        """Get a (flaat) UserInfos object from given OIDC Access Token."""
        user_infos = super().get_user_infos_from_access_token(access_token, issuer_hint)
        if (
            user_infos is not None
            and user_infos.user_info is not None
            and user_infos.access_token_info is not None
        ):
            # HACK for wlcg OP: copy groups from AT body in 'wlcg.groups' claim
            # to 'groups' claim in userinfo; also needed by feudalAdapter
            wlcg_groups = user_infos.access_token_info.body.get("wlcg.groups", None)
            if wlcg_groups is not None:
                if "groups" in user_infos.user_info:
                    user_infos.user_info["groups"] += [
                        g for g in wlcg_groups if g not in user_infos.user_info["groups"]
                    ]
                else:
                    user_infos.user_info["groups"] = wlcg_groups
        return user_infos

    def get_uid_from_request(self, request: Request):
        """Get a (flaat) UserInfos object from given request.
        OIDC Access Token should be found in request headers.
        """
        try:
            user_infos = self.get_user_infos_from_request(request)
        except Exception:  # pylint: disable=broad-except
            return None
        if user_infos is None:
            return None
        return {"sub": user_infos.subject, "iss": user_infos.issuer}

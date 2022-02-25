from typing import Optional
import logging

from fastapi import Request
from flaat import AuthWorkflow
from flaat.config import AccessLevel
from flaat.fastapi import Flaat
from flaat.requirements import CheckResult, Requirement
from flaat.user_infos import UserInfos
from flaat.exceptions import FlaatException

from .config import Config, OPAuthZ, canonical_url
from .exceptions import Unauthorised, BadRequest
from .utils import AuthorisationType


logger = logging.getLogger(__name__)

# We dynamically load the requirement in is_satisfied_by
class AuthRequirement(Requirement):
    def __init__(self, authorisation: dict):
        self.authorisation = authorisation


class AuthenticatedUserRequirement(AuthRequirement):
    def is_satisfied_by(self, user_infos: UserInfos) -> CheckResult:
        op_authz = OPAuthZ.load(self.authorisation, user_infos)
        if op_authz is None:
            return CheckResult(False, "OP is not configured")

        return CheckResult(True, "OP is configured")


class AuthorisedUserRequirement(AuthRequirement):
    def is_satisfied_by(self, user_infos: UserInfos) -> CheckResult:
        op_authz = OPAuthZ.load(self.authorisation, user_infos)
        if op_authz is None:
            return CheckResult(False, "OP is not configured")

        return op_authz.get_user_requirement().is_satisfied_by(user_infos)


class AuthorisedAdminRequirement(AuthRequirement):
    def is_satisfied_by(self, user_infos: UserInfos) -> CheckResult:
        op_authz = OPAuthZ.load(self.authorisation, user_infos)
        if op_authz is None:
            return CheckResult(False, "OP is not configured")

        return op_authz.get_admin_requirement().is_satisfied_by(user_infos)


class Authorisation(Flaat):
    """
    Extension for Flaat:
    - configures Flaat parameters in given config file
    - more flexible authorisation:
        - per OP configuration
        - individual user authorisation
    - stringify authorisation info
    """

    def __init__(self, config: Config):
        super().__init__()
        self.set_trusted_OP_list(config.trusted_ops)
        self.set_verbosity(config.verbosity)
        self.__authorisation = config.authorisation
        self.access_levels = [
            AccessLevel(
                "authenticated_user", AuthenticatedUserRequirement(self.__authorisation)
            ),
            AccessLevel(
                "authorised_user", AuthorisedUserRequirement(self.__authorisation)
            ),
            AccessLevel(
                "authorised_admin", AuthorisedAdminRequirement(self.__authorisation)
            ),
        ]

    def info(self, request: Request) -> dict:
        # get OP from request
        try:
            user_infos = self.get_user_infos_from_request(request)
        except FlaatException as e:
            logger.info(f"Error while trying to get user infos from request: {e}")
            user_infos = None
        if user_infos is None:
            raise Unauthorised("Could not get user infos from request.")
        op_authz = OPAuthZ.load(self.__authorisation, user_infos)
        # if OP not supported
        if op_authz is None:
            return {
                "OP": user_infos.issuer,
                **AuthorisationType.not_supported.description()
            }
        # if all users from this OP are authorised
        if op_authz.authorise_all:
            return {
                "OP": op_authz.op_url,
                **AuthorisationType.all_users.description()
            }
        # if authorised VOs are specified
        if len(op_authz.authorised_vos) > 0:
            return {
                "OP": op_authz.op_url,
                **AuthorisationType.vo_based.description(vo_match=op_authz.vo_match),
                "supported_VOs": op_authz.authorised_vos
            }
        # if individual users are specified
        if len(op_authz.authorised_users) > 0:
            return {
                "OP": op_authz.op_url,
                **AuthorisationType.individual_users.description(),
            }

        # OP is supported but no authorisation is configured
        return {
            "OP": op_authz.op_url,
            **AuthorisationType.not_configured.description()
        }

    # def authenticated_user_required(self, func):
    #     @wraps(func)
    #     def wrapper(*args, **kwargs):
    #         # get request from wrapped function params
    #         request = kwargs.get("request", None)
    #         if request is None:
    #             self.set_last_error("No request object found.")
    #             logging.getLogger(__name__).error(f"{self.get_last_error()}")
    #             raise BadRequest(f"{self.get_last_error()}")
    #         # get uid from request
    #         userinfo = self.get_uid_from_request(request)
    #         if userinfo is None:
    #             logging.getLogger(__name__).error(f"Could not use token to get userinfo from userinfo endpoints. Last error: {self.get_last_error()}.")
    #             raise Unauthorised("Failed to use provided token to get token issuer or sub.")
    #         # get OP and sub from userinfo
    #         op_url = userinfo.get("iss", None)
    #         sub = userinfo.get("sub", None)
    #         if op_url is None:
    #             logging.getLogger(__name__).error(self.get_last_error())
    #             raise Unauthorised("Could not determine token issuer. Token is not a JWT or OP not supported.")
    #         # get authorisation info for this OP
    #         op_authz = self.__authorisation.get(canonical_url(op_url), None)

    #         # if OP not supported:
    #         if op_authz is None:
    #             msg = f"The token issuer is not supported on this service: {op_url}"
    #             logging.getLogger(__name__).error(msg)
    #             raise Unauthorised(msg)

    #         @self.login_required()
    #         async def tmp(*args, **kwargs):
    #             return await func(*args, **kwargs)
    #         return tmp(*args, **kwargs)
    #     return wrapper

    # def authorised_user_required(self, func):
    #     @wraps(func)
    #     def wrapper(*args, **kwargs):
    #         # get request from wrapped function params
    #         request = kwargs.get("request", None)
    #         if request is None:
    #             self.set_last_error("No request object found.")
    #             logging.getLogger(__name__).error(f"{self.get_last_error()}")
    #             raise BadRequest(f"{self.get_last_error()}")
    #         # get uid from request
    #         userinfo = self.get_uid_from_request(request)
    #         if userinfo is None:
    #             logging.getLogger(__name__).error(f"Could not use token to get userinfo from userinfo endpoints. Last error: {self.get_last_error()}.")
    #             raise Unauthorised("Failed to use provided token to get token issuer or sub.")
    #         # get OP and sub from userinfo
    #         op_url = userinfo.get("iss", None)
    #         sub = userinfo.get("sub", None)
    #         if op_url is None:
    #             logging.getLogger(__name__).error(self.get_last_error())
    #             raise Unauthorised("Could not determine token issuer. Token is not a JWT or OP not supported.")
    #         # get authorisation info for this OP
    #         op_authz = self.__authorisation.get(canonical_url(op_url), None)

    #         # if OP not supported:
    #         if op_authz is None:
    #             msg = f"The token issuer is not supported on this service: {op_url}"
    #             logging.getLogger(__name__).error(msg)
    #             raise Unauthorised(msg)

    #         # if all users from this OP are authorised,
    #         # it is sufficient to require login, which validates the token
    #         # at the userinfo endpoint
    #         if to_bool(op_authz.get('authorise_all', 'False')):
    #             logging.getLogger(__name__).warning(f"Authorising all users from {op_url}."
    #                                                 "We recommend setting the authorised_vos field in motley_cue.conf.")

    #             @self.login_required()
    #             async def tmp(*args, **kwargs):
    #                 return await func(*args, **kwargs)
    #             return tmp(*args, **kwargs)

    #         # if this user is specifically authorised,
    #         # it is sufficient to require login, which validates the token
    #         # at the userinfo endpoint
    #         authorised_users = to_list(op_authz.get('authorised_users', '[]'))
    #         if len(authorised_users) > 0:
    #             if sub is None:
    #                 logging.getLogger(__name__).error(self.get_last_error())
    #                 raise Unauthorised("Could not determine user's 'sub' claim.")
    #             if sub in authorised_users:
    #                 logging.getLogger(__name__).debug(f"User {sub} is individually authorised by sub.")

    #                 @self.login_required()
    #                 async def tmp(*args, **kwargs):
    #                     return await func(*args, **kwargs)
    #                 return tmp(*args, **kwargs)
    #             logging.getLogger(__name__).debug(f"User {sub} is not individually authorised by sub.")
    #         else:
    #             logging.getLogger(__name__).debug("No individual users authorised by sub.")

    #         # if authorised VOs are specified, try to authorise based on VOs
    #         # this depends on the type of VO: AARC-G002 compatible or not
    #         # HACK: if at least on of the provided groups is not compatible with AARC-G002,
    #         # treat them all as normal groups
    #         # possible FIX: flaat should deal with it and provide a uniform interface to check
    #         # VO membership for mixed lists of VOs
    #         authorised_vos = to_list(op_authz.get('authorised_vos', '[]'))
    #         if len(authorised_vos) > 0:
    #             try:
    #                 logging.getLogger(__name__).debug(
    #                     f"Trying VO-based authorisation for user {sub}; list of authorised VOs: {authorised_vos}.")
    #                 _ = [Aarc_g002_entitlement(vo, strict=False)
    #                      for vo in authorised_vos]

    #                 @self.aarc_g002_entitlement_required(
    #                     entitlement=authorised_vos,
    #                     claim=op_authz['vo_claim'],
    #                     match=op_authz['vo_match']
    #                 )
    #                 async def tmp(*args, **kwargs):
    #                     return await func(*args, **kwargs)
    #                 return tmp(*args, **kwargs)
    #             except Aarc_g002_entitlement_Error:
    #                 logging.getLogger(__name__).warning(
    #                     "The provided VOs are not compatible with AARC G002. Will use string comparison.")

    #                 @self.group_required(
    #                     group=authorised_vos,
    #                     claim=op_authz['vo_claim'],
    #                     match=op_authz['vo_match']
    #                 )
    #                 async def tmp(*args, **kwargs):
    #                     return await func(*args, **kwargs)
    #                 return tmp(*args, **kwargs)
    #         else:
    #             logging.getLogger(__name__).debug(f"No authorised VOs specified for {op_url}.")

    #         # user not authorised
    #         logging.getLogger(__name__).error(
    #             f"User {sub} from {op_url} was not authorised to access the service.")
    #         raise Unauthorised("You are not authorised to access this service.")
    #     return wrapper

    # def authorised_admin_required(self, func):
    #     @wraps(func)
    #     def wrapper(*args, **kwargs):
    #         # get request from wrapped function params
    #         request = kwargs.get("request", None)
    #         if request is None:
    #             self.set_last_error("No request object found.")
    #             logging.getLogger(__name__).error(f"{self.get_last_error()}")
    #             raise BadRequest(f"{self.get_last_error()}")
    #         # get uid from request
    #         userinfo = self.get_uid_from_request(request)
    #         if userinfo is None:
    #             logging.getLogger(__name__).error(f"Could not use token to get userinfo from userinfo endpoints. Last error: {self.get_last_error()}.")
    #             raise Unauthorised("Failed to use provided token to get token issuer or sub.")
    #         # get OP and sub from userinfo
    #         op_url = userinfo.get("iss", None)
    #         sub = userinfo.get("sub", None)
    #         if op_url is None:
    #             logging.getLogger(__name__).error(self.get_last_error())
    #             raise Unauthorised(f"Could not determine token issuer. Token is not a JWT or OP not supported.")
    #         # get authorisation info for this OP
    #         op_authz = self.__authorisation.get(canonical_url(op_url), None)
    #         # if OP not supported:
    #         if op_authz is None:
    #             msg = f"The token issuer is not supported on this service: {op_url}"
    #             logging.getLogger(__name__).error(msg)
    #             raise Unauthorised(msg)

    #         # check if sub in request is authorised to be admin
    #         authorised_admins = to_list(op_authz.get('authorised_admins', '[]'))
    #         if len(authorised_admins) > 0:
    #             if sub is None:
    #                 logging.getLogger(__name__).error(self.get_last_error())
    #                 raise Unauthorised("Could not determine admin user's 'sub' claim.")
    #             if sub in authorised_admins:
    #                 logging.getLogger(__name__).debug(f"Sub {sub} is an authorised admin.")
    #                 # get iss of user to suspend/resume from wrapped function params
    #                 user_iss = kwargs.get("iss", None)
    #                 if user_iss is None:
    #                     self.set_last_error("Bad Request: No user issuer provided.")
    #                     logging.getLogger(__name__).error(f"{self.get_last_error()}")
    #                     raise BadRequest(f"{self.get_last_error()}")
    #                 # check if admin's issuer matches user's issuer
    #                 logging.getLogger(__name__).debug(f"Checking if admin {sub} is authorised for given user's iss, i.e. "
    #                                                   f"{user_iss} == {op_url}: "
    #                                                   f"{canonical_url(user_iss) == canonical_url(op_url)}")
    #                 if canonical_url(user_iss) == canonical_url(op_url):
    #                     is_authorised = True
    #                     # HACK: if the URLs are the same (in canonical form) use the admin URL instead.
    #                     # This URL is in the form found in ATs released by this OP.
    #                     # This means you can leave out the "https://" of ending "/" in admin API calls and it still works.
    #                     # Otherwise, feudal_adapter cannot find the user since it queries by gecos field: sub@iss
    #                     # FIXME: can also be done in feudal, or by storing the exact URL in the mapper
    #                     # print(op_url, user_iss)
    #                     logging.getLogger(__name__).warning(f"Changing iss of user to perform admin action on: {user_iss} => {op_url}")
    #                     kwargs["iss"] = op_url
    #                 else:
    #                     # the admin iss does not match the user iss,
    #                     # check if admin is authorised for all OPs
    #                     is_authorised = to_bool(op_authz.get('authorise_admins_for_all_ops', 'False'))
    #                     logging.getLogger(__name__).debug(f"Checking if {sub} is authorised as admin for all OPs: {is_authorised}")
    #                     # HACK: still try to overwrite user iss with the url as stored in flaat, but first check EXACT_OP_URLS for exceptions
    #                     if is_authorised:
    #                         for iss in EXACT_OP_URLS + self.trusted_op_list:
    #                             if canonical_url(user_iss) == canonical_url(iss):
    #                                 logging.getLogger(__name__).warning(f"Changing iss of user to perform admin action on: {user_iss} => {iss}")
    #                                 kwargs["iss"] = iss
    #                                 break
    #                 if is_authorised:
    #                     @self.login_required()
    #                     async def tmp(*args, **kwargs):
    #                         return await func(*args, **kwargs)
    #                     return tmp(*args, **kwargs)
    #                 else:
    #                     msg = "You are not authorised to perform actions on users from other OPs."
    #                     logging.getLogger(__name__).error(f"Admin {sub} from {op_url} is not authorised to perform actions on users from other OPs (i.e. {user_iss})")
    #                     raise Unauthorised(msg)
    #         else:
    #             logging.getLogger(__name__).debug("No admins authorised by sub.")

    #         logging.getLogger(__name__).error(f"User {sub} from {op_url} is not authorised as admin on this service")
    #         raise Unauthorised("You are not authorised as admin on this service.")
    #     return wrapper


    def authenticated_user_required(self, func):
        return self.access_level("authenticated_user")(func)

    def authorised_user_required(self, func):
        return self.access_level("authorised_user")(func)

    def authorised_admin_required(self, func):
        def _check_request(user_infos: UserInfos, *_, **kwargs) -> CheckResult:
            user_iss = kwargs.get("iss", "")
            if user_iss != "":
                op_authz = OPAuthZ.load(self.__authorisation, user_infos)
                if op_authz is None:
                    return CheckResult(False, "No OP config")

                if (
                    not op_authz.authorise_admins_for_all_ops
                    and op_authz.op_url != canonical_url(user_iss)
                ):
                    return CheckResult(
                        False,
                        f"Admin {user_infos} is not authorised to manage users of issuer '{user_iss}'",
                    )

            return CheckResult(True, "Request is authorised")

        auth_flow = AuthWorkflow(
            self,
            user_requirements=self._get_access_level_requirement("authorised_admin"),
            request_requirements=_check_request,
        )
        return auth_flow.decorate_view_func(func)

    def get_user_infos_from_access_token(self, access_token) -> Optional[UserInfos]:
        try:
            user_infos = super().get_user_infos_from_access_token(access_token)
        except Exception:
            return None
        if (
            user_infos is not None
            and user_infos.user_info is not None
            and user_infos.access_token_info is not None
        ):
            # HACK for wlcg OP: copy groups from AT body in 'wlcg.groups' claim to 'groups' claim in userinfo
            # also needed by feudalAdapter
            wlcg_groups = user_infos.access_token_info.body.get("wlcg.groups", None)
            if wlcg_groups is not None:
                if "groups" in user_infos.user_info:
                    user_infos.user_info["groups"] += wlcg_groups
                else:
                    user_infos.user_info["groups"] = wlcg_groups
        return user_infos

    def get_uid_from_request(self, request: Request):
        try:
            user_infos = self.get_user_infos_from_request(request)
        except Exception:
            return None
        if user_infos is None:
            return None
        return {"sub": user_infos.subject, "iss": user_infos.issuer}

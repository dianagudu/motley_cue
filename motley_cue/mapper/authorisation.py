from typing import Optional

from fastapi import Request
from flaat import AccessLevel, AuthWorkflow
from flaat.fastapi import Flaat
from flaat.requirements import CheckResult, Requirement
from flaat.user_infos import UserInfos

from .config import Config, OPAuthZ, canonical_url


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
        user_infos = self.get_user_infos_from_request(request)
        if user_infos is None:
            return {
                "content": "No user infos",
                "status_code": 401,
            }
        op_authz = OPAuthZ.load(self.__authorisation, user_infos)
        # if OP not supported
        if op_authz is None:
            return {
                "content": {
                    "OP": user_infos.issuer,
                    "info": "OP is not supported or provided URL is invalid",
                },
            }
        # if all users from this OP are authorised
        if op_authz.authorise_all:
            return {
                "content": {
                    "OP": op_authz.op_url,
                    "info": "All users from this OP are authorised",
                },
                "status_code": 200,
            }
        # if authorised VOs are specified
        if len(op_authz.authorised_vos) > 0:
            return {
                "content": {
                    "OP": op_authz.op_url,
                    "info": "VO-based authorisation",
                    "description": f"Users who are in {op_authz.vo_match} of the supported VOs are authorised",
                    "supported VOs": op_authz.authorised_vos,
                },
            }
        # OP is supported but no authorisation is configured
        # (or individual users are authorised, but we don't print those)
        return {
            "content": {
                "OP": op_authz.op_url,
                "info": "OP is supported but no VO-based or OP-wide authorisation configured.",
                "description": "Users might still be authorised on an individual basis. Please contact the service administrator to request access.",
            },
        }

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
        user_infos = super().get_user_infos_from_access_token(access_token)
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
        user_infos = self.get_user_infos_from_request(request)
        if user_infos is None:
            return None
        return {"sub": user_infos.subject, "iss": user_infos.issuer}

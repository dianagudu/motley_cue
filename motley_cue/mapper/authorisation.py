import logging
from functools import wraps
from fastapi import Request
from flaat import Flaat, tokentools
from aarc_g002_entitlement import Aarc_g002_entitlement, Aarc_g002_entitlement_Error

from .config import canonical_url, to_bool, to_list
from .utils import MapperResponse


class Authorisation(Flaat):
    """
    Extension for Flaat:
    - configures Flaat parameters in given config file
    - more flexible authorisation:
        - per OP configuration
        - individual user authorisation
    - stringify authorisation info
    """

    def __init__(self, config):
        super().__init__()
        super().set_web_framework("fastapi")
        super().set_cache_lifetime(120)  # seconds; default is 300
        super().set_trusted_OP_list(config.trusted_ops)
        super().set_verbosity(config.verbosity)
        self.__authorisation = config.authorisation
        # create list of OPs supported on service that do not support JWT tokens
        self.__non_jwt_ops = []
        ops_that_support_jwt_canonical = [canonical_url(op) for op in self.ops_that_support_jwt]
        for iss in self.trusted_op_list:
            if canonical_url(iss) not in ops_that_support_jwt_canonical:
                self.__non_jwt_ops += [iss]
        logging.getLogger(__name__).debug(f"List of OPs that do not support JWT ATs: {self.__non_jwt_ops}")

    def info(self, request):
        # get OP from request
        userinfo = self.get_uid_from_request(request)
        op_url = userinfo.get("iss", None)
        if op_url is None:
            return {
                "content": "Bad Token: no issuer found in Access Token",
                "status_code": 400
            }
        op_authz = self.__authorisation.get(canonical_url(op_url), None)
        # if OP not supported
        if op_authz is None:
            return {
                "content": {
                    "OP": op_url,
                    "info": "OP is not supported or provided URL is invalid"
                },
                "status_code": 200
            }
        # if all users from this OP are authorised
        if to_bool(op_authz.get('authorise_all', 'False')):
            return {
                "content": {
                    "OP": op_url,
                    "info": "All users from this OP are authorised"
                },
                "status_code": 200
            }
        # if authorised VOs are specified
        authorised_vos = to_list(op_authz.get('authorised_vos', '[]'))
        if len(authorised_vos) > 0:
            return {
                "content": {
                    "OP": op_url,
                    "info": "VO-based authorisation",
                    "description": f"Users who are in {str(op_authz['vo_match'])} of the supported VOs are authorised",
                    "supported VOs": authorised_vos
                },
                "status_code": 200
            }
        # OP is supported but no authorisation is configured
        # (or individual users are authorised, but we don't print those)
        return {
            "content": {
                "OP": op_url,
                "info": "OP is supported but no VO-based or OP-wide authorisation configured.",
                "description": "Users might still be authorised on an individual basis. Please contact the service administrator to request access."
            },
            "status_code": 200
        }

    def authorised_user_required(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # get request from wrapped function params
            request = kwargs.get("request", None)
            if request is None:
                self.set_last_error("No request object found.")
                logging.getLogger(__name__).error(f"{self.get_last_error()}")
                return MapperResponse(f"{self.get_last_error()}", 401)
            # get OP and sub from request
            userinfo = self.get_uid_from_request(request)
            op_url = userinfo.get("iss", None)
            sub = userinfo.get("sub", None)
            if op_url is None:
                logging.getLogger(__name__).error(self.get_last_error())
                return MapperResponse(f"Bad Token: no issuer found in Access Token: {self.get_last_error()}", 401)
            # get authorisation info for this OP
            op_authz = self.__authorisation.get(canonical_url(op_url), None)

            # if OP not supported:
            if op_authz is None:
                msg = f"The token issuer is not supported on this service: {op_url}"
                logging.getLogger(__name__).error(msg)
                return MapperResponse(msg, 403)

            # if all users from this OP are authorised,
            # it is sufficient to require login, which validates the token
            # at the userinfo endpoint
            if to_bool(op_authz.get('authorise_all', 'False')):
                logging.getLogger(__name__).warning(f"Authorising all users from {op_url}."
                                                    "We recommend setting the authorised_vos field in motley_cue.conf.")

                @self.login_required()
                async def tmp(*args, **kwargs):
                    return await func(*args, **kwargs)
                return tmp(*args, **kwargs)

            # if this user is specifically authorised,
            # it is sufficient to require login, which validates the token
            # at the userinfo endpoint
            authorised_users = to_list(op_authz.get('authorised_users', '[]'))
            if len(authorised_users) > 0:
                if sub is None:
                    logging.getLogger(__name__).error(self.get_last_error())
                    return MapperResponse(f"Bad Token: no sub claim found in Access Token: {self.get_last_error()}", 401)
                if sub in authorised_users:
                    logging.getLogger(__name__).debug(f"User {sub} is individually authorised by sub.")

                    @self.login_required()
                    async def tmp(*args, **kwargs):
                        return await func(*args, **kwargs)
                    return tmp(*args, **kwargs)
                logging.getLogger(__name__).debug(f"User {sub} is not individually authorised by sub.")
            else:
                logging.getLogger(__name__).debug("No individual users authorised by sub.")

            # if authorised VOs are specified, try to authorise based on VOs
            # this depends on the type of VO: AARC-G002 compatible or not
            # HACKY: if at least on of the provided groups is not compatible with AARC-G002,
            # treat them all as normal groups
            # possible FIX: flaat should deal with it and provide a uniform interface to check
            # VO membership for mixed lists of VOs
            authorised_vos = to_list(op_authz.get('authorised_vos', '[]'))
            if len(authorised_vos) > 0:
                try:
                    logging.getLogger(__name__).debug(
                        f"Trying VO-based authorisation for user {sub}; list of authorised VOs: {authorised_vos}.")
                    _ = [Aarc_g002_entitlement(vo, strict=False)
                         for vo in authorised_vos]

                    @self.aarc_g002_entitlement_required(
                        entitlement=authorised_vos,
                        claim=op_authz['vo_claim'],
                        match=op_authz['vo_match']
                    )
                    async def tmp(*args, **kwargs):
                        return await func(*args, **kwargs)
                    return tmp(*args, **kwargs)
                except Aarc_g002_entitlement_Error:
                    logging.getLogger(__name__).warning(
                        "The provided VOs are not compatible with AARC G002. Will use string comparison.")

                    @self.group_required(
                        group=authorised_vos,
                        claim=op_authz['vo_claim'],
                        match=op_authz['vo_match']
                    )
                    async def tmp(*args, **kwargs):
                        return await func(*args, **kwargs)
                    return tmp(*args, **kwargs)
            else:
                logging.getLogger(__name__).debug(f"No authorised VOs specified for {op_url}.")

            # user not authorised
            logging.getLogger(__name__).error(
                f"User {sub} from {op_url} was not authorised to access the service.")
            return MapperResponse("Forbidden: you are not authorised to access this service", 403)
        return wrapper

    def authorised_admin_required(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # get request from wrapped function params
            request = kwargs.get("request", None)
            if request is None:
                self.set_last_error("No request object found.")
                logging.getLogger(__name__).error(f"{self.get_last_error()}")
                return MapperResponse(f"{self.get_last_error()}", 401)
            # get OP and sub from request
            userinfo = self.get_uid_from_request(request)
            op_url = userinfo.get("iss", None)
            sub = userinfo.get("sub", None)
            if op_url is None:
                logging.getLogger(__name__).error(self.get_last_error())
                return MapperResponse(f"Bad Token: no issuer found in Access Token: {self.get_last_error()}", 401)
            # get authorisation info for this OP
            op_authz = self.__authorisation.get(canonical_url(op_url), None)
            # if OP not supported:
            if op_authz is None:
                msg = f"The token issuer is not supported on this service: {op_url}"
                logging.getLogger(__name__).error(msg)
                return MapperResponse(msg, 403)

            # check if sub in request is authorised to be admin
            authorised_admins = to_list(op_authz.get('authorised_admins', '[]'))
            if len(authorised_admins) > 0:
                if sub is None:
                    logging.getLogger(__name__).error(self.get_last_error())
                    return MapperResponse(f"Bad Token: no sub claim found in Access Token: {self.get_last_error()}", 401)
                if sub in authorised_admins:
                    logging.getLogger(__name__).debug(f"Sub {sub} is an authorised admin.")
                    # check if admin is authorised for all OPs or if admin's issuer matches user's issuer
                    is_authorised = to_bool(op_authz.get('authorise_admins_for_all_ops', 'False'))
                    logging.getLogger(__name__).debug(f"Checking if {sub} is authorised as admin for all OPs: {is_authorised}")
                    if not is_authorised:
                        # get iss of user to suspend/resume from wrapped function params
                        user_iss = kwargs.get("iss", None)
                        if user_iss is None:
                            self.set_last_error("Bad Request: No user issuer provided.")
                            logging.getLogger(__name__).error(f"{self.get_last_error()}")
                            return MapperResponse(f"{self.get_last_error()}", 400)
                        logging.getLogger(__name__).debug(f"Checking if admin {sub} is authorised for given user, i.e. "
                                                          f"{user_iss} == {op_url}: "
                                                          f"{canonical_url(user_iss) == canonical_url(op_url)}")
                        if canonical_url(user_iss) == canonical_url(op_url):
                            is_authorised = True
                            # HACKY: if the URLs are the same (in canonical form) use the admin URL instead
                            # this URL is in the form found in ATs released by this OP
                            # this means you can leave out the "https://" of ending "/" in admin API calls and it still works
                            # otherwise, feudal_adapter cannot find the user since it queries by gecos field: sub@iss
                            # BUT it doesn't work when admins can suspend users from other OPs
                            # FIXME: can to be done in feudal, or by storing the exact URL in the mapper
                            # print(op_url, user_iss)
                            kwargs["iss"] = op_url
                    if is_authorised:
                        @self.login_required()
                        async def tmp(*args, **kwargs):
                            return await func(*args, **kwargs)
                        return tmp(*args, **kwargs)
                    else:
                        msg = "Forbidden: you are not authorised to perform actions on users from other OPs"
                        logging.getLogger(__name__).error(f"Admin {sub} from {op_url} is not authorised to perform actions on users from other OPs (i.e. {user_iss})")
                        MapperResponse(msg, 403)
            else:
                logging.getLogger(__name__).debug("No admins authorised by sub.")

            logging.getLogger(__name__).error(f"User {sub} from {op_url} is not authorised as admin on this service")
            return MapperResponse("Forbidden: you are not authorised as admin on this service", 403)
        return wrapper

    def get_userinfo_from_request(self, request: Request):
        token = tokentools.get_access_token_from_request(request)
        iss = tokentools.get_issuer_from_accesstoken_info(token)
        if iss:
            # assume JWT
            logging.getLogger(__name__).debug(f"Found issuer URL in AT: {iss}")
            userinfo = self.get_info_from_userinfo_endpoints(token)
            if not userinfo:
                return None
            # add issuer to userinfo  -> needed by feudalAdapter
            userinfo["iss"] = iss
            # HACK for wlcg OP: copy groups from AT body in 'wlcg.groups' claim to 'groups' claim in userinfo
            # also needed by feudalAdapter
            at_info = self.get_info_thats_in_at(token)
            try:
                wlcg_groups = at_info["body"]["wlcg.groups"]
                logging.getLogger(__name__).info(f"Found 'wlcg.groups' in token, will add them to 'groups' claim: {wlcg_groups}")
                if not userinfo.get("groups", None):
                    userinfo["groups"] = wlcg_groups
                else:
                    userinfo["groups"] += wlcg_groups
            except:
                pass
        else:
            # non JWT AT
            logging.getLogger(__name__).debug("Could not find issuer URL in AT, probably not a JTW")
            userinfo = self.get_userinfo_non_jwt(token)
        return userinfo

    def get_uid_from_request(self, request: Request):
        token = tokentools.get_access_token_from_request(request)
        iss = tokentools.get_issuer_from_accesstoken_info(token)
        if iss:
            # assume JWT
            logging.getLogger(__name__).debug(f"Found issuer URL in AT: {iss}")
            try:
                token_info = tokentools.get_accesstoken_info(token)
                sub = token_info["body"]["sub"]
            except Exception:
                # somehow, no sub found in JWT, even though iss was there
                # go to user endpoint
                logging.getLogger(__name__).debug("No sub found in AT, trying to query userinfo endpoint...")
                userinfo = self.get_info_from_userinfo_endpoints(token)
                if userinfo.get("iss", None):
                    sub = userinfo["iss"]
                else:
                    return None
        else:
            # non JWT AT
            logging.getLogger(__name__).debug("Could not find issuer URL in AT, probably not a JWT")
            userinfo = self.get_userinfo_non_jwt(token)
            if not userinfo:
                return None
            iss = userinfo["iss"]
            sub = userinfo["sub"]
        return {
            "sub": sub,
            "iss": iss
        }

    def get_userinfo_non_jwt(self, token):
        logging.getLogger(__name__).debug(f"Trying all OPs that do not support JWTs...")
        for iss in self.__non_jwt_ops:
            logging.getLogger(__name__).debug(f"Trying OP URL: {iss}")
            self.set_trusted_OP(iss)
            userinfo = self.get_info_from_userinfo_endpoints(token)
            self.iss = None
            if userinfo:
                userinfo["iss"] = iss
                return userinfo
        return None
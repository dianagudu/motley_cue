import logging
from functools import wraps
from fastapi import Request
from flaat import Flaat, tokentools
from aarc_g002_entitlement import Aarc_g002_entitlement, Aarc_g002_entitlement_Error

from .config import canonical_url, to_bool, to_list
from .utils import MapperResponse, EXACT_OP_URLS


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

    def info(self, request):
        # get OP from request
        token = tokentools.get_access_token_from_request(request)
        op_url = self.get_issuer_from_accesstoken(token)
        if op_url is None:
            return {
                "content": "Bad Token: no issuer found in Access Token or cache",
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
            # get uid from request
            userinfo = self.get_uid_from_request(request)
            if userinfo is None:
                logging.getLogger(__name__).error(f"Could not use token to get userinfo from userinfo endpoints. Last error: {self.get_last_error()}.")
                return MapperResponse(f"Forbidden: you are not authorised to access this service. Failed to use provided token to get userinfo.", 401)
            # get OP and sub from userinfo
            op_url = userinfo.get("iss", None)
            sub = userinfo.get("sub", None)
            if op_url is None:
                logging.getLogger(__name__).error(self.get_last_error())
                return MapperResponse(f"Bad Token: no issuer found in Access Token.", 401)
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
                    return MapperResponse(f"Bad Token: no sub claim found in Access Token.", 401)
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
            # HACK: if at least on of the provided groups is not compatible with AARC-G002,
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
            # get uid from request
            userinfo = self.get_uid_from_request(request)
            if userinfo is None:
                logging.getLogger(__name__).error(f"Could not use token to get userinfo from userinfo endpoints. Last error: {self.get_last_error()}.")
                return MapperResponse(f"Forbidden: you are not authorised to access this service. Failed to use provided token to get userinfo.", 401)
            # get OP and sub from userinfo
            op_url = userinfo.get("iss", None)
            sub = userinfo.get("sub", None)
            if op_url is None:
                logging.getLogger(__name__).error(self.get_last_error())
                return MapperResponse(f"Bad Token: no issuer found in Access Token.", 401)
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
                    return MapperResponse(f"Bad Token: no sub claim found in Access Token.", 401)
                if sub in authorised_admins:
                    logging.getLogger(__name__).debug(f"Sub {sub} is an authorised admin.")
                    # get iss of user to suspend/resume from wrapped function params
                    user_iss = kwargs.get("iss", None)
                    if user_iss is None:
                        self.set_last_error("Bad Request: No user issuer provided.")
                        logging.getLogger(__name__).error(f"{self.get_last_error()}")
                        return MapperResponse(f"{self.get_last_error()}", 400)
                    # check if admin's issuer matches user's issuer
                    logging.getLogger(__name__).debug(f"Checking if admin {sub} is authorised for given user's iss, i.e. "
                                                      f"{user_iss} == {op_url}: "
                                                      f"{canonical_url(user_iss) == canonical_url(op_url)}")
                    if canonical_url(user_iss) == canonical_url(op_url):
                        is_authorised = True
                        # HACK: if the URLs are the same (in canonical form) use the admin URL instead.
                        # This URL is in the form found in ATs released by this OP.
                        # This means you can leave out the "https://" of ending "/" in admin API calls and it still works.
                        # Otherwise, feudal_adapter cannot find the user since it queries by gecos field: sub@iss
                        # FIXME: can also be done in feudal, or by storing the exact URL in the mapper
                        # print(op_url, user_iss)
                        logging.getLogger(__name__).warning(f"Changing iss of user to perform admin action on: {user_iss} => {op_url}")
                        kwargs["iss"] = op_url
                    else:
                        # the admin iss does not match the user iss,
                        # check if admin is authorised for all OPs
                        is_authorised = to_bool(op_authz.get('authorise_admins_for_all_ops', 'False'))
                        logging.getLogger(__name__).debug(f"Checking if {sub} is authorised as admin for all OPs: {is_authorised}")
                        # HACK: still try to overwrite user iss with the url as stored in flaat, but first check EXACT_OP_URLS for exceptions
                        if is_authorised:
                            for iss in EXACT_OP_URLS + self.trusted_op_list:
                                if canonical_url(user_iss) == canonical_url(iss):
                                    logging.getLogger(__name__).warning(f"Changing iss of user to perform admin action on: {user_iss} => {iss}")
                                    kwargs["iss"] = iss
                                    break
                    if is_authorised:
                        @self.login_required()
                        async def tmp(*args, **kwargs):
                            return await func(*args, **kwargs)
                        return tmp(*args, **kwargs)
                    else:
                        msg = "Forbidden: you are not authorised to perform actions on users from other OPs"
                        logging.getLogger(__name__).error(f"Admin {sub} from {op_url} is not authorised to perform actions on users from other OPs (i.e. {user_iss})")
                        return MapperResponse(msg, 403)
            else:
                logging.getLogger(__name__).debug("No admins authorised by sub.")

            logging.getLogger(__name__).error(f"User {sub} from {op_url} is not authorised as admin on this service")
            return MapperResponse("Forbidden: you are not authorised as admin on this service", 403)
        return wrapper

    def get_userinfo_from_request(self, request: Request):
        token = tokentools.get_access_token_from_request(request)
        try:
            userinfo = self.get_info_from_userinfo_endpoints(token)
        except Exception as e:
            logging.getLogger(__name__).debug(f"Exception while getting userinfo from userinfo endpoints: {e}")
            return None
        if not userinfo:
            self.set_last_error("Could not get userinfo from userinfo endpoints.")
            return None
        try:
            iss = self.get_issuer_from_accesstoken(token)
        except Exception as e:
            logging.getLogger(__name__).debug(f"Exception while getting issuer from Access Token or cache: {e}")
            return None
        if iss:
            logging.getLogger(__name__).debug(f"Found issuer URL in AT or cache: {iss}")
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
            logging.getLogger(__name__).debug("Could not get issuer URL from Access Token or cache.")
        return userinfo

    def get_uid_from_request(self, request: Request):
        token = tokentools.get_access_token_from_request(request)
        try:
            iss = self.get_issuer_from_accesstoken(token)
        except Exception as e:
            logging.getLogger(__name__).debug(f"Exception while getting issuer from Access Token or cache: {e}")
            return None
        if iss:
            logging.getLogger(__name__).debug(f"Found issuer URL in AT or cache: {iss}")
            try:
                token_info = tokentools.get_accesstoken_info(token)
                sub = token_info["body"]["sub"]
            except Exception:
                # somehow, no sub found in JWT, even though iss was there
                # go to user endpoint
                logging.getLogger(__name__).debug("No sub found in AT, trying to query userinfo endpoint...")
                userinfo = self.get_info_from_userinfo_endpoints(token)
                sub = userinfo.get("sub", None)
        else:
            logging.getLogger(__name__).debug("Could not get issuer URL from Access Token or cache.")
            return None
        if not sub:
            return None
        return {
            "sub": sub,
            "iss": iss
        }

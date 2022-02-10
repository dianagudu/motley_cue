from enum import Enum


# store here the exact URL for some OPs as found in an AT issued by them
# e.g. some have a trailing slash, but flaat strips that off
EXACT_OP_URLS = [
    'https://wlcg.cloud.cnaf.infn.it/',
    'https://aai.egi.eu/oidc/',
]


class AuthorisationType(Enum):
    not_supported = ("not supported", "OP is not supported.")
    not_configured = ("not configured", "OP is supported but no authorisation is configured.")
    all_users = ("all users", "All users from this OP are authorised.")
    individual_users = ("individual users", "Users are authorised on an individual basis. Please contact a service administrator to request access.")
    vo_based = ("VO-based", "Users who are in {} of the supported VOs are authorised")

    def __init__(self, mode, info):
        self.__mode = mode
        self.__info = info

    def description(self, vo_match="one"):
        return {
            "authorisation_type": self.__mode,
            "authorisation_info": self.__info.format(vo_match)
        }

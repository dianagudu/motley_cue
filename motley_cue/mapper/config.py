"""Module for loading and describing motley_cue configuration.
"""
from configparser import ConfigParser
from typing import List, Optional, Dict
import logging
import os
from pathlib import Path
from dataclasses import dataclass, fields, field

from flaat.requirements import (
    IsTrue,
    OneOf,
    AllOf,
    Requirement,
    Unsatisfiable,
    get_vo_requirement,
    get_audience_requirement,
)

from .exceptions import InternalException


class Config:
    """Class for motley_cue configuration."""

    def __init__(self, config_parser):
        """Create a configuration object from a ConfigParser.

        Args:
            config_parser (ConfigParser): ConfigParser object

        Raises:
            InternalException: if configuration does not contain mandatory section [mapper]
        """
        self.CONFIG = Configuration.load(config_parser)

        self.__trusted_ops = [
            entry.op_url for entry in self.CONFIG.authorisation.all_op_authz.values()
        ]
        self.__info_ops = {
            canonical_url(entry.op_url): entry.get_info()
            for entry in self.CONFIG.authorisation.all_op_authz.values()
        }

    def get_op_info(self, op_url: str) -> Optional[Dict]:
        """Get information about an OP.

        Args:
            op_url (str): OP URL

        Returns:
            Optional[Dict]: information about the OP
        """
        return self.__info_ops.get(canonical_url(op_url))

    @property
    def trusted_ops(self):
        """Return list of trusted OPs"""
        return self.__trusted_ops

    @property
    def authorisation(self):
        """Return all authorisation sections in configuration"""
        return self.CONFIG.authorisation

    @property
    def log_file(self):
        """Return log file name"""
        return self.CONFIG.mapper.log_file

    @property
    def log_level(self):
        """return log level"""
        return self.CONFIG.mapper.log_level

    @property
    def docs_url(self):
        """return url to be used as location for swagger docs"""
        return self.CONFIG.mapper.docs_url if self.CONFIG.mapper.enable_docs else None

    @property
    def otp(self):
        """Return OTP configuration"""
        return self.CONFIG.otp

    @property
    def privacy(self):
        """Return privacy policy configuration"""
        return self.CONFIG.privacy

    @property
    def verbosity(self):
        """
        Translate given log level to verbosity needed by flaat as follows:
            CRITICAL -> 0
            ERROR -> 1
            WARNING / WARN -> 1
            INFO -> 2
            DEBUG -> 3
        default is 1
        """
        if self.log_level == "CRITICAL":
            return 0
        if self.log_level in ["ERROR", "WARNING", "WARN"]:
            return 1
        if self.log_level == "INFO":
            return 2
        if self.log_level == "DEBUG":
            return 3
        return 1

    @staticmethod
    def from_files(list_of_config_files: List):
        """Load motley_cue configuration from given list of files.
        Processing is stopped, once a give file is found.

        If no configuration is found in given list, default locations are checked.
        If none of the files exist, raise an InternalException.
        """
        list_of_config_files.extend(Config._reload_motley_cue_configs())
        config_parser = ConfigParser()
        for filename in list_of_config_files:
            fpath = Path(filename)
            if fpath.exists():
                files_read = config_parser.read(fpath)
                logging.getLogger(__name__).debug("Read config from %s", files_read)
                return Config(config_parser)
        raise InternalException(
            "No configuration file found at given or default locations: " f"{list_of_config_files}"
        )

    @staticmethod
    def _reload_motley_cue_configs():
        """Return a list of default configuration paths.

        Config locations, by priority:
        $MOTLEY_CUE_CONFIG
        ./motley_cue.conf
        ~/.config/motley_cue/motley_cue.conf
        /etc/motley_cue/motley_cue.conf
        """
        files = []
        filename = os.environ.get("MOTLEY_CUE_CONFIG")
        if filename:
            files += [Path(filename)]
        files += [
            Path("motley_cue.conf").absolute(),
            Path("~/.config/motley_cue/motley_cue.conf").expanduser(),
        ]
        files += [Path("/etc/motley_cue/motley_cue.conf")]
        return files


def to_bool(bool_str):
    """Convert a string to bool.
    Raise an InternalException if the string cannot be converted.
    """
    if bool_str.lower() in ["true", "yes", "1"]:
        return True
    if bool_str.lower() in ["false", "no", "0"]:
        return False
    raise InternalException(f"Error reading config file: unrecognised boolean value {bool_str}.")


def to_list(list_str):
    """Convert a string to a list.
    Raise an InternalException if the string is not a valid list, with square brackets.
    """
    # remove all whitespace
    stripped_list_str = list_str.replace("\n", "").replace(" ", "").replace("\t", "")
    # strip list of square brackets
    if stripped_list_str.startswith("[") and stripped_list_str.endswith("]"):
        stripped_list_str = stripped_list_str[1:-1].strip(",")
    else:
        raise InternalException(
            f"Could not parse string as list, must be contained in square brackets: {list_str}"
        )
    # check empty list
    if stripped_list_str == "":
        return []
    return [v.strip('"').strip("'") for v in stripped_list_str.split(",")]


def to_int(int_str):
    """Convert a string to int.
    Raise a FatalError if the string cannot be converted.
    """
    try:
        return int(int_str)
    except ValueError:
        raise InternalException(f"Error converting to int: unrecognised integer value {int_str}.")


def to_loglevel(loglevel_str):
    """Convert a string to a loglevel.
    Raise a FatalError if the string cannot be converted.
    """
    if loglevel_str.upper() in logging._nameToLevel.keys():
        return logging._nameToLevel[loglevel_str.upper()]
    raise InternalException(f"Error reading config file: unrecognised loglevel {loglevel_str}.")


def canonical_url(url: str) -> str:
    """Strip URL of protocol info and ending slashes"""
    url = url.lower()
    if url.startswith("http://"):
        url = url[7:]
    if url.startswith("https://"):
        url = url[8:]
    if url.startswith("www."):
        url = url[4:]
    if url.endswith("/"):
        url = url[:-1]
    return url


@dataclass
class ConfigSection:
    @classmethod
    def __section__name__(cls):
        return "DEFAULT"

    @classmethod
    def load(cls, config: ConfigParser, section_name: Optional[str] = None):
        """Sets only the fields that are present in the config file"""
        try:
            if section_name is None:
                section_name = cls.__section__name__()
            field_names = set(f.name for f in fields(cls))
            return cls(**{k: v for k, v in {**config[section_name]}.items() if k in field_names})
        except KeyError:
            # logger.debug(
            #     "Missing config section %s, using default values.", cls.__section__name__()
            # )
            return cls()

    def __post_init__(self):
        """Converts some of the fields to the correct type"""
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                continue
            field_type = field.type
            if hasattr(field.type, "__module__") and field.type.__module__ == "typing":
                if field.type.__str__().startswith(
                    "typing.Optional"
                ) or field.type.__str__().startswith("typing.Union"):
                    field_type = field.type.__args__[0]  # get the type of the field
                elif field.type.__str__().startswith("typing.List"):
                    field_type = list  # treat as a list
                else:
                    return  # no conversion
            # if the field does not have the hinted type, convert it if possible
            if not isinstance(value, field_type):
                if field_type == int:
                    setattr(self, field.name, to_int(value))
                if field_type == bool:
                    setattr(self, field.name, to_bool(value))
                if field_type in [List, List[str], list]:
                    setattr(self, field.name, to_list(value))

    def to_dict(self) -> dict:
        """Converts the config to a dict"""
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass
class ConfigMapper(ConfigSection):
    """Config section for ldf_adapter."""

    log_level: str = "WARNING"
    log_file: Optional[str] = None  # equivalent to /dev/stderr
    enable_docs: bool = False
    docs_url: str = "/docs"

    @classmethod
    def __section__name__(cls):
        return "mapper"


@dataclass
class ConfigOTP(ConfigSection):
    """Config section for OTP."""

    use_otp: bool = False
    backend: str = "sqlite"
    db_location: str = "/var/cache/motley_cue/tokenmap.db"
    keyfile: str = "/var/lib/motley_cue/motley_cue.key"

    @classmethod
    def __section__name__(cls):
        return "mapper.otp"


@dataclass
class ConfigPrivacy(ConfigSection):
    """Config section for privacy policy."""

    privacy_contact: str = "NOT CONFIGURED"
    privacy_file: str = "/etc/motley_cue/privacystatement.md"

    @classmethod
    def __section__name__(cls):
        return "privacy"


@dataclass
class ConfigOPAuthZ(ConfigSection):
    """Config section for authorisation of one OP."""

    op_url: str = ""
    scopes: list = field(default_factory=list)
    # user authorisation
    authorise_all: bool = False
    authorised_users: list = field(default_factory=list)
    authorised_vos: list = field(default_factory=list)
    vo_claim: str = "eduperson_entitlement"
    vo_match: str = "one"
    audience: str = ""
    # admin authorisation
    authorised_admins: list = field(default_factory=list)
    authorise_admins_for_all_ops: bool = False

    def get_info(self) -> dict:
        """Returns a dict with the info for this OP"""
        return {
            "op_url": self.op_url,
            "scopes": self.scopes,
            "audience": self.audience,
        }

    # methods used in conjunction with flaat
    def get_user_requirement(self) -> Requirement:
        """Creates a (flaat) Requirement object from this authorisation configuration,
        for API users.
        """
        req = OneOf()
        if self.authorise_all:
            user_has_same_issuer = lambda user_infos: canonical_url(
                user_infos.issuer
            ) == canonical_url(self.op_url)
            req.add_requirement(IsTrue(user_has_same_issuer))

        if len(self.authorised_vos) > 0:
            vo_claim = self.vo_claim
            vo_match = self.vo_match
            req.add_requirement(
                get_vo_requirement(self.authorised_vos, claim=vo_claim, match=vo_match)
            )

        if len(self.authorised_users) > 0:
            user_has_sub = lambda user_infos: user_infos.subject in self.authorised_users
            req.add_requirement(IsTrue(user_has_sub))

        all_req = AllOf()
        all_req.add_requirement(req)
        all_req.add_requirement(get_audience_requirement(self.audience))

        return all_req

    def get_admin_requirement(self) -> Requirement:
        """Creates a (flaat) Requirement object from this authorisation configuration,
        for API admins.
        """
        if len(self.authorised_admins) > 0:
            user_has_sub = lambda user_infos: user_infos.subject in self.authorised_admins
            return IsTrue(user_has_sub)

        return Unsatisfiable()


# Add more config sections here by inheriting from ConfigSection and providing a __section__name__
# method that returns the section name. The section name is used to load the right section from the
# config file. Provide default values for all fields in the class. The fields will be set to the
# values from the config file if they are present, otherwise the default values will be used.
# Then add a new field to the Configuration class below with the type of this section class.


@dataclass
class ConfigAuthorisation:
    """All authorisation configs for all supported OPs."""

    all_op_authz: Dict[str, ConfigOPAuthZ] = field(default_factory=dict)

    @classmethod
    def load(cls, config: ConfigParser):
        """Loads all config sub-sections that start with the given section name"""
        subsection_prefix = "authorisation"
        all_op_authz = {}
        for section in config.sections():
            if section.startswith(f"{subsection_prefix}."):
                op_config = ConfigOPAuthZ.load(config, section_name=section)
                all_op_authz[canonical_url(op_config.op_url)] = op_config
        return cls(all_op_authz)

    def to_dict(self) -> dict:
        """Converts the config to a dict"""
        return {k: v.to_dict() for k, v in self.all_op_authz.items()}

    def get_op_authz(self, user_infos) -> Optional[ConfigOPAuthZ]:
        """Returns the ConfigOPAuthZ object for OP given in user_infos.

        Args:
            user_infos: (flaat) UserInfo object

        Returns:
            Optional[OPAuthZ]: OPAuthZ object
        """
        return self.all_op_authz.get(canonical_url(user_infos.issuer), None)


@dataclass
class Configuration:
    """All configuration settings for motley_cue."""

    mapper: ConfigMapper = ConfigMapper()
    otp: ConfigOTP = ConfigOTP()
    privacy: ConfigPrivacy = ConfigPrivacy()
    authorisation: ConfigAuthorisation = ConfigAuthorisation()

    @classmethod
    def load(cls, config: ConfigParser):
        """Loads all config settings from the given config parser"""
        return cls(**{f.name: f.type.load(config) for f in fields(cls)})

    def to_dict(self) -> dict:
        """Converts the config to a dict"""
        return {field.name: getattr(self, field.name).to_dict() for field in fields(self)}

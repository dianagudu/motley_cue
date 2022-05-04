"""Module for loading and describing motley_cue configuration.
"""
from __future__ import annotations
from configparser import ConfigParser
from typing import List, Optional
import logging
import os
from pathlib import Path
from dataclasses import dataclass

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
        if config_parser.has_section("mapper"):
            config_mapper = config_parser["mapper"]
        else:
            raise InternalException("No [mapper] configuration found in configuration file!")
        # log level
        self.__log_level = config_mapper.get("log_level", logging.WARNING)
        # log file
        self.__log_file = config_mapper.get("log_file", None)
        # swagger docs
        if to_bool(config_mapper.get("enable_docs", "False")):
            self.__docs_url = config_mapper.get("docs_url", "/docs")
        else:
            self.__docs_url = None
        # use OTPs as a replacement for long (>1k) access tokens
        otp_dict = {}
        if config_parser.has_section("mapper.otp"):
            otp_dict = dict(config_parser["mapper.otp"])
        self.__otp = OTPConfig(otp_dict)
        # trusted OPs
        authz_sections = [
            section for section in config_parser.sections() if section.startswith("authorisation")
        ]
        self.__trusted_ops = []
        self.__authorisation = {}
        for section in authz_sections:
            op_url = config_parser[section].get("op_url", None)
            if op_url is not None:
                self.__trusted_ops.append(op_url)
                self.__authorisation[canonical_url(op_url)] = dict(config_parser[section].items())

    def get_authorisation(self, op_url):
        """Return authorisation section in configuration for OP given by URL"""
        return self.__authorisation[op_url]

    @property
    def trusted_ops(self):
        """Return list of trusted OPs"""
        return self.__trusted_ops

    @property
    def authorisation(self):
        """Return all authorisation sections in configuration"""
        return self.__authorisation

    @property
    def log_file(self):
        """Return log file name"""
        return self.__log_file

    @property
    def log_level(self):
        """return log level"""
        return self.__log_level

    @property
    def docs_url(self):
        """return url to be used as location for swagger docs"""
        return self.__docs_url

    @property
    def otp(self):
        """Return whether OTPs are enabled"""
        return self.__otp

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
        if self.__log_level == "CRITICAL":
            return 0
        if self.__log_level in ["ERROR", "WARNING", "WARN"]:
            return 1
        if self.__log_level == "INFO":
            return 2
        if self.__log_level == "DEBUG":
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


def canonical_url(url):
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


def to_bool(bool_str):
    """Convert a string to bool.
    Raise an InternalException if the string cannot be converted.
    """
    if bool_str.lower() == "true":
        return True
    if bool_str.lower() == "false":
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


class OPAuthZ:
    """Class describing the authorisation configuration for an OP."""

    # pylint: disable=too-many-instance-attributes
    # nine is reasonable in this case.
    def __init__(self, op_authz: dict):
        """Initialises all fields from given dict or with default values,
        and converts them to the appropriate type when necessary.

        Args:
            op_authz (dict): ConfigParser section for authorisation
        """
        self.op_url = canonical_url(op_authz.get("op_url", ""))
        self.authorise_all = to_bool(op_authz.get("authorise_all", "False"))
        self.authorise_admins_for_all_ops = to_bool(
            op_authz.get("authorise_admins_for_all_ops", "False")
        )
        self.authorised_users = to_list(op_authz.get("authorised_users", "[]"))
        self.authorised_admins = to_list(op_authz.get("authorised_admins", "[]"))
        self.authorised_vos = to_list(op_authz.get("authorised_vos", "[]"))
        self.vo_claim = op_authz.get("vo_claim", "")
        self.vo_match = op_authz.get("vo_match", "")
        self.audience = op_authz.get("audience", "")

    @classmethod
    def load(cls, authorisation, user_infos) -> Optional[OPAuthZ]:
        """Creates an OPAuthZ object for OP given in user_infos.

        Args:
            authorisation: configuration dict containing all authorisation sections.
            user_infos: (flaat) UserInfo object

        Returns:
            Optional[OPAuthZ]: OPAuthZ object
        """
        op_authz = authorisation.get(canonical_url(user_infos.issuer), None)
        if op_authz is None:
            return None
        return cls(op_authz)

    def get_user_requirement(self) -> Requirement:
        """Creates a (flaat) Requirement object from this authorisation configuration,
        for API users.
        """
        req = OneOf()
        if self.authorise_all:
            user_has_same_issuer = (
                lambda user_infos: canonical_url(user_infos.issuer) == self.op_url
            )
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


@dataclass
class OTPConfig:
    """Class describing the OTP configuration"""

    def __init__(self, otp_config: dict) -> None:
        """Initialises all fields from given dict or with default values,
        and converts them to the appropriate type when necessary.

        Args:
            otp_config (dict): ConfigParser section for OTP
        """
        self.use_otp = to_bool(otp_config.get("use_otp", "False"))
        self.backend = otp_config.get("backend", "sqlite").lower()
        self.db_location = otp_config.get("db_location", "/run/motley_cue/tokenmap.db")
        self.keyfile = otp_config.get("keyfile", "/run/motley_cue/motley_cue.key")

from __future__ import annotations
from configparser import ConfigParser
from typing import List, Optional
import logging
import os
from pathlib import Path

from flaat.requirements import IsTrue, OneOf, Requirement, Unsatisfiable, get_vo_requirement

from .exceptions import InternalException


class Config():
    def __init__(self, config_parser):
        try:
            config_mapper = config_parser['mapper']
        except:
            raise InternalException("No [mapper] configuration found in configuration file!")
        # log level
        self.__log_level = config_mapper.get(
            'log_level', logging.WARNING)
        # log file
        self.__log_file = config_mapper.get(
            'log_file', None
        )
        # swagger docs
        if config_mapper.get("enable_docs", False):
            self.__docs_url = config_mapper.get("docs_url", "/docs")
        else:
            self.__docs_url = None
        # trusted OPs
        authz_sections = [section for section in config_parser.sections()
                          if section.startswith("authorisation")]
        self.__trusted_ops = []
        self.__authorisation = {}
        for section in authz_sections:
            op_url = config_parser[section].get('op_url', None)
            if op_url is not None:
                self.__trusted_ops.append(op_url)
                self.__authorisation[canonical_url(op_url)] = dict(
                    config_parser[section].items())

    def get_authorisation(self, op_url):
        return self.__authorisation[op_url]

    @property
    def trusted_ops(self):
        return self.__trusted_ops

    @property
    def authorisation(self):
        return self.__authorisation

    @property
    def log_file(self):
        return self.__log_file

    @property
    def log_level(self):
        return self.__log_level

    @property
    def docs_url(self):
        return self.__docs_url

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
        elif self.__log_level in ["ERROR", "WARNING", "WARN"]:
            return 1
        elif self.__log_level == "INFO":
            return 2
        elif self.__log_level == "DEBUG":
            return 3
        else:
            return 1

    @staticmethod
    def from_files(list_of_config_files: List):
        list_of_config_files.extend(Config._reload_motley_cue_configs())
        config_parser = ConfigParser()
        for filename in list_of_config_files:
            f = Path(filename)
            if f.exists():
                files_read = config_parser.read(f)
                logging.getLogger(__name__).debug(F"Read config from {files_read}")
                return Config(config_parser)
        raise InternalException(f"No configuration file found at given or default locations: {list_of_config_files}")

    @staticmethod
    def _reload_motley_cue_configs():
        """Reload configuration from disk.

        Config locations, by priority:
        $MOTLEY_CUE_CONFIG
        ./motley_cue.conf
        ~/.config/motley_cue/motley_cue.conf
        /etc/motley_cue/motley_cue.conf

        processing is stopped, once a give file is found
        """
        files = []
        filename = os.environ.get("MOTLEY_CUE_CONFIG")
        if filename:
            files += [Path(filename)]
        files += [
            Path("motley_cue.conf").absolute(),
            Path("~/.config/motley_cue/motley_cue.conf").expanduser()
        ]
        files += [Path("/etc/motley_cue/motley_cue.conf")]
        return files


def canonical_url(url):
    """Strip URL of protocol info and ending slashes
    """
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
    """
    if bool_str.lower() == "true":
        return True
    elif bool_str.lower() == "false":
        return False
    else:
        raise InternalException(f"Error reading config file: unrecognised boolean value {bool_str}.")


def to_list(list_str):
    """Convert a string to a list.
    """
    # remove all whitespace
    stripped_list_str = list_str.replace("\n", "")\
        .replace(" ", "").replace("\t", "")
    # strip list of square brackets
    if stripped_list_str.startswith("[") and stripped_list_str.endswith("]"):
        stripped_list_str = stripped_list_str[1:-1].strip(",")
    else:
        raise InternalException(f"Could not parse string as list, must be contained in square brackets: {list_str}")
    # check empty list
    if stripped_list_str == "":
        return []
    return [v.strip('"').strip("'") for v in stripped_list_str.split(",")]


class OPAuthZ:
    def __init__(self, op_authz: dict):
        self.op_url = canonical_url(op_authz.get("op_url",""))
        self.authorise_all = to_bool(op_authz.get("authorise_all","False"))
        self.authorise_admins_for_all_ops = to_bool(op_authz.get("authorise_admins_for_all_ops","False"))
        self.authorised_users = to_list(op_authz.get("authorised_users", "[]"))
        self.authorised_admins = to_list(op_authz.get("authorised_admins", "[]"))
        self.authorised_vos = to_list(op_authz.get("authorised_vos", "[]"))
        self.vo_claim = op_authz.get("vo_claim", "")
        self.vo_match = op_authz.get("vo_match", "")

    @classmethod
    def load(cls, authorisation, user_infos) -> Optional[OPAuthZ]:
        op_authz = authorisation.get(canonical_url(user_infos.issuer), None)
        if op_authz is None:
            return None
        return cls(op_authz)

    def get_user_requirement(self) -> Requirement:
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

        return req

    def get_admin_requirement(self) -> Requirement:
        if len(self.authorised_admins) > 0:
            user_has_sub = lambda user_infos: user_infos.subject in self.authorised_admins
            return IsTrue(user_has_sub)

        return Unsatisfiable()

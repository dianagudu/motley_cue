import os
import logging
from pathlib import Path
from configparser import ConfigParser


class Config():
    def __init__(self, config_parser):
        # log level
        self.__log_level = config_parser['mapper'].get(
            'log_level', logging.WARNING)
        # log file
        self.__log_file = config_parser['mapper'].get(
            'log_file', None
        )
        # swagger docs
        if config_parser['mapper'].get("enable_docs", False):
            self.__docs_url = config_parser['mapper'].get("docs_url", "/docs")
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
    def from_default_files():
        return Config.from_files(Config._reload_motley_cue_configs())

    @staticmethod
    def from_files(list_of_config_files):
        config_parser = ConfigParser()
        for f in list_of_config_files:
            if f.exists():
                files_read = config_parser.read(f)
                logging.getLogger(__name__).debug(F"Read config from {files_read}")
                break
        return Config(config_parser)

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
            Path('motley_cue.conf'),
            Path.home()/'.config'/'motley_cue'/'motley_cue.conf'
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
    return True if bool_str.lower() == 'true' else False


def to_list(list_str):
    """Convert a string to a list.
    """
    # strip list of square brackets and remove all whitespace
    stripped_list_str = list_str.replace("\n", "")\
        .replace(" ", "").replace("\t", "")\
        .strip("][").rstrip(",")
    # check empty list
    if stripped_list_str == "":
        return []
    return [v.strip('"').strip("'") for v in stripped_list_str.split(",")]

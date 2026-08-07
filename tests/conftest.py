from configparser import ConfigParser
from io import StringIO
from typing import Callable, Dict
import pytest
from starlette.testclient import TestClient
import sys
import os

from .utils import (
    MockTokenManager,
    MockUser,
    mock_flaat_get_user_infos_from_access_token,
)


def with_writable_otp_paths(config_file: ConfigParser, tmp_path) -> ConfigParser:
    """Return a copy of `config_file` with [mapper.otp] pointed at tmp_path,
    unless the test set those options itself.

    The shipped defaults live under /var/lib/motley_cue, which only the service
    user can create -- deliberately, since that directory holds the token
    database and the key that decrypts the Access Tokens in it. Tests do not run
    as that user, so give them somewhere writable instead of weakening the
    default.

    Returns a copy because the CONFIG_* parsers in configs.py are module-level
    singletons shared by every test; mutating one here would leak these paths
    into tests that assert on the defaults.
    """
    buffer = StringIO()
    config_file.write(buffer)
    config_copy = ConfigParser()
    config_copy.read_string(buffer.getvalue())

    if not config_copy.has_section("mapper.otp"):
        config_copy.add_section("mapper.otp")
    if not config_copy.has_option("mapper.otp", "keyfile"):
        config_copy.set("mapper.otp", "keyfile", str(tmp_path / "motley_cue.key"))
    if not config_copy.has_option("mapper.otp", "db_location"):
        config_copy.set("mapper.otp", "db_location", str(tmp_path / "tokenmap.db"))
    return config_copy


@pytest.fixture()
def test_api(
    config_file, method_to_patch: str, callback: Callable[..., Dict], monkeypatch, tmp_path
):
    with monkeypatch.context() as mp:
        # patch the config to return minimal config instead of reading through files
        from motley_cue.mapper import config

        config_file = with_writable_otp_paths(config_file, tmp_path)
        mp.setattr(config.Config, "from_files", lambda x: config.Config(config_file))

        # monkeypatch global mapper to let all users through
        from motley_cue.dependencies import mapper

        mp.setattr(mapper, "authenticated_user_required", lambda x: x)
        mp.setattr(mapper, "authorised_user_required", lambda x: x)
        mp.setattr(mapper, "authorised_admin_required", lambda x: x)
        # monkeypatch given mapper method
        if method_to_patch != "":
            mp.setattr(mapper, method_to_patch, callback)

        # import FastAPI object here to make sure its decorators are based on monkeypatched mapper
        from motley_cue.api import api

        test_client = TestClient(api)
        yield test_client

        # unload all motley_cue modules
        for m in [x for x in sys.modules if x.startswith("motley_cue")]:
            del sys.modules[m]


@pytest.fixture()
def test_authorisation(config_file: ConfigParser, monkeypatch):
    with monkeypatch.context() as mp:
        from motley_cue.mapper import authorisation, config

        mp.setattr(
            "motley_cue.mapper.authorisation.Flaat.get_user_infos_from_access_token",
            mock_flaat_get_user_infos_from_access_token,
        )
        authz = authorisation.Authorisation(config.Config(config_file))
        yield authz

        # unload all motley_cue modules
        for m in [x for x in sys.modules if x.startswith("motley_cue")]:
            del sys.modules[m]


@pytest.fixture()
def test_local_user_manager():
    from motley_cue.mapper import local_user_management

    lum = local_user_management.LocalUserManager()
    yield lum


@pytest.fixture()
def test_local_user_manager_patched(monkeypatch, mocker: Callable[[str, str], Callable]):
    with monkeypatch.context() as mp:
        # mock User class to only contain a mock reach_state method,
        # which returns a valid response, either successful or failed
        from ldf_adapter import User

        mp.setattr(User, "__init__", MockUser.__init__)
        mp.setattr(User, "reach_state", mocker)
        mp.setattr(User, "resume", mocker)

        from motley_cue.mapper import local_user_management

        lum = local_user_management.LocalUserManager()
        yield lum


@pytest.fixture()
def test_unauthorised():
    from motley_cue.mapper.exceptions import Unauthorised

    yield Unauthorised


@pytest.fixture()
def test_bad_request():
    from motley_cue.mapper.exceptions import BadRequest

    yield BadRequest


@pytest.fixture()
def test_internal_server_error():
    from motley_cue.mapper.exceptions import InternalServerError

    yield InternalServerError


@pytest.fixture()
def test_internal_exception():
    from motley_cue.mapper.exceptions import InternalException

    yield InternalException


@pytest.fixture()
def test_config():
    from motley_cue.mapper import config

    yield config


@pytest.fixture()
def test_encryption():
    from motley_cue.mapper import token_manager

    yield token_manager.Encryption


@pytest.fixture()
def test_token_manager(monkeypatch):
    with monkeypatch.context() as mp:
        from motley_cue.mapper.token_manager import TokenManager
        from motley_cue.mapper.config import ConfigOTP

        mp.setattr(TokenManager, "__init__", MockTokenManager.__init__)
        mp.setattr(TokenManager, "_new_otp", MockTokenManager._new_otp)
        mp.setattr(TokenManager, "database", MockTokenManager.database)

        yield TokenManager(ConfigOTP(use_otp=True))


@pytest.fixture()
def test_token_manager_original_new_otp(monkeypatch):
    with monkeypatch.context() as mp:
        from motley_cue.mapper.token_manager import TokenManager
        from motley_cue.mapper.config import ConfigOTP

        mp.setattr(TokenManager, "__init__", MockTokenManager.__init__)
        mp.setattr(TokenManager, "database", MockTokenManager.database)

        yield TokenManager(ConfigOTP(use_otp=True))


@pytest.fixture()
def test_token_db(backend):
    from motley_cue.mapper import token_manager

    keyfile = "tmp_keyfile"
    db_location = "tmp.db"

    if backend == "sqlite":
        db = token_manager.SQLiteTokenDB(db_location, keyfile)
    elif backend == "sqlitedict":
        db = token_manager.SQLiteDictTokenDB(db_location, keyfile)
    elif backend == "memory":
        db = token_manager.MemorySQLiteTokenDB(keyfile)
    else:
        raise ValueError(f"Unknown backend: {backend}")

    yield db

    if os.path.exists(keyfile):
        os.remove(keyfile)
    if os.path.exists(f"{backend}_{db_location}"):
        os.remove(f"{backend}_{db_location}")
    if isinstance(db, token_manager.MemorySQLiteTokenDB):
        db.close()

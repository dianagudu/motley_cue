from configparser import ConfigParser
from typing import Callable, Dict
import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def test_api(config_file, method_to_patch: str, callback: Callable[..., Dict], monkeypatch):
    with monkeypatch.context() as mp:
        # patch the config to return minimal config instead of reading through files
        from motley_cue.mapper import config
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
        print(api.docs_url)
        test_api = TestClient(api)
        yield test_api


@pytest.fixture()
def test_authorisation(config_file: ConfigParser):
    from motley_cue.mapper import authorisation, config
    authz = authorisation.Authorisation(config.Config(config_file))
    yield authz


@pytest.fixture()
def test_local_user_manager():
    from motley_cue.mapper import local_user_management
    lum = local_user_management.LocalUserManager()
    yield lum
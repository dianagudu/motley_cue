import pytest

from .test_env import MC_TOKEN

def test_lum_login_info(test_local_user_manager):
    assert test_local_user_manager.login_info() == {
        "description": "Local SSH Test Service",
        "login_help": "Login via `mccli ssh {login_host}`.",
        "ssh_host": "localhost",
    }

def test_deploy(test_local_user_manager):
    pass

import pytest

from .utils import (
    mock_deployed_result,
    mock_exception,
    mock_not_deployed_result,
    mock_status_result,
)
from .utils import mock_failure, mock_rejection, mock_exception
from .utils import MOCK_ISS, MOCK_SUB


def test_lum_login_info(test_local_user_manager):
    assert test_local_user_manager.login_info() == {
        "description": "Local SSH Test Service",
        "login_help": "Login via `mccli ssh {login_host}`.",
        "ssh_host": "localhost",
    }


@pytest.mark.parametrize("mocker", [mock_deployed_result()])
def test_deploy_success(test_local_user_manager_patched):
    response = test_local_user_manager_patched.deploy({})
    assert response["state"] == "deployed"
    assert set(response.keys()) == set(["state", "message", "credentials"])


@pytest.mark.parametrize("mocker", [mock_failure(), mock_exception()])
def test_deploy_fail(test_local_user_manager_patched, test_internal_server_error):
    with pytest.raises(test_internal_server_error):
        test_local_user_manager_patched.deploy({})


@pytest.mark.parametrize("mocker", [mock_rejection()])
def test_deploy_reject(test_local_user_manager_patched, test_unauthorised):
    with pytest.raises(test_unauthorised):
        test_local_user_manager_patched.deploy({})


@pytest.mark.parametrize(
    "mocker",
    [
        *[
            mock_status_result(state=state)
            for state in [
                "deployed",
                "not_deployed",
                "rejected",
                "pending",
                "suspended",
                "limited",
                "unknown",
            ]
        ],
        mock_not_deployed_result(),
    ],
)
def test_get_status_success(test_local_user_manager_patched):
    response = test_local_user_manager_patched.get_status({})
    assert set(response.keys()) == set(["state", "message"])


@pytest.mark.parametrize("mocker", [mock_exception()])
def test_get_status_fail(test_local_user_manager_patched, test_internal_server_error):
    with pytest.raises(test_internal_server_error):
        test_local_user_manager_patched.get_status({})


@pytest.mark.parametrize(
    "mocker",
    [
        *[
            mock_status_result(state=state)
            for state in ["suspended", "not_deployed", "rejected", "pending", "unknown"]
        ],
        mock_not_deployed_result(),
    ],
)
def test_suspend_success(test_local_user_manager_patched):
    response = test_local_user_manager_patched.suspend({})
    assert set(response.keys()) == set(["state", "message"])


@pytest.mark.parametrize("mocker", [mock_exception()])
def test_suspend_fail(test_local_user_manager_patched, test_internal_server_error):
    with pytest.raises(test_internal_server_error):
        test_local_user_manager_patched.suspend({})


@pytest.mark.parametrize(
    "mocker",
    [
        *[
            mock_status_result(state=state)
            for state in ["suspended", "not_deployed", "rejected", "pending", "unknown"]
        ],
        mock_not_deployed_result(),
    ],
)
def test_admin_suspend_success(test_local_user_manager_patched):
    response = test_local_user_manager_patched.admin_suspend(sub=MOCK_SUB, iss=MOCK_ISS)
    assert set(response.keys()) == set(["state", "message"])


@pytest.mark.parametrize("mocker", [mock_exception()])
def test_admin_suspend_fail(test_local_user_manager_patched, test_internal_server_error):
    with pytest.raises(test_internal_server_error):
        test_local_user_manager_patched.admin_suspend(sub=MOCK_SUB, iss=MOCK_ISS)


@pytest.mark.parametrize(
    "mocker",
    [
        *[
            mock_status_result(state=state)
            for state in [
                "deployed",
                "not_deployed",
                "rejected",
                "pending",
                "limited",
                "unknown",
            ]
        ],
        mock_not_deployed_result(),
    ],
)
def test_admin_resume_success(test_local_user_manager_patched):
    response = test_local_user_manager_patched.admin_resume(sub=MOCK_SUB, iss=MOCK_ISS)
    assert set(response.keys()) == set(["state", "message"])


@pytest.mark.parametrize("mocker", [mock_exception()])
def test_admin_resume_fail(test_local_user_manager_patched, test_internal_server_error):
    with pytest.raises(test_internal_server_error):
        test_local_user_manager_patched.admin_resume(sub=MOCK_SUB, iss=MOCK_ISS)


@pytest.mark.parametrize(
    "mocker,username,verified",
    [
        *[
            (mock_status_result(state=state, username="same_user"), "same_user", True)
            for state in ["deployed", "suspended", "limited", "pending"]
        ],
        *[
            (mock_status_result(state=state, username="same_user"), username, False)
            for state in ["deployed", "suspended", "limited", "pending"]
            for username in ["not_same_user", "", None]
        ],
        *[(mock_not_deployed_result(), username, False) for username in ["user", "", None]],
        *[
            (mock_status_result(state="rejected"), username, False)
            for username in ["user", "", None]
        ],
        *[
            (mock_status_result(state="unknown"), username, False)
            for username in ["user", "", None]
        ],
    ],
)
def test_verify_user_success(test_local_user_manager_patched, username: str, verified: bool):
    response = test_local_user_manager_patched.verify_user({}, username)
    assert set(response.keys()) == set(["state", "verified"])
    assert response["verified"] == verified


@pytest.mark.parametrize(
    "mocker,username",
    [
        (mocker(), username)
        for mocker in [mock_exception, mock_rejection, mock_failure]
        for username in ["any_username", "", None]
    ],
)
def test_verify_user_fail(
    test_local_user_manager_patched, test_internal_server_error, username: str
):
    with pytest.raises(test_internal_server_error):
        test_local_user_manager_patched.verify_user({}, username)


@pytest.mark.parametrize(
    "mocker",
    [
        mock_deployed_result(),
        mock_not_deployed_result(),
        *[
            mock_status_result(state=state)
            for state in [
                "deployed",
                "not_deployed",
                "rejected",
                "pending",
                "suspended",
                "limited",
                "unknown",
            ]
        ],
        mock_failure(),
        mock_rejection(),
        mock_exception(),
    ],
)
def test_reach_state_no_userinfo(test_local_user_manager_patched, test_internal_server_error):
    with pytest.raises(test_internal_server_error):
        state = 0  # any number (of State type)
        test_local_user_manager_patched._reach_state(None, state)

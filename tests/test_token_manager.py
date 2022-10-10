import pytest
import os
import string
from cryptography.fernet import Fernet
from fastapi import Request

from .utils import (
    MOCK_TOKEN,
    MOCK_REQUEST,
    MOCK_HEADERS,
    MOCK_OTP,
    MOCK_OTP_REQUEST,
    MOCK_OTP_HEADERS,
    mock_exception,
)


def test_encryption(test_encryption):
    keyfile = "tmp_keyfile"
    secret = "this is my secret string to be encrypted"

    encryption = test_encryption(keyfile)
    assert oct(os.stat(keyfile).st_mode & 0o777) == "0o400"
    assert secret == encryption.decrypt(encryption.encrypt(secret))

    os.remove(keyfile)


def test_encryption_keyfile_exists(test_encryption):
    keyfile = "tmp_keyfile"
    secret = "this is my secret string to be encrypted"

    key = Fernet.generate_key()
    open(keyfile, "wb").write(key)

    encryption = test_encryption(keyfile)
    assert secret == encryption.decrypt(encryption.encrypt(secret))

    os.remove(keyfile)


def test_encryption_keyfile_exists_not_a_key(test_encryption):
    keyfile = "tmp_keyfile"

    open(keyfile, "wb").write(b"random not a key")

    with pytest.raises(Exception):
        _ = test_encryption(keyfile)

    os.remove(keyfile)


def test_encryption_keyfile_exists_not_bytes(test_encryption):
    keyfile = "tmp_keyfile"

    open(keyfile, "w").write("random not a key")

    with pytest.raises(Exception):
        _ = test_encryption(keyfile)

    os.remove(keyfile)


@pytest.mark.parametrize(
    "token",
    ["", "random string", 100 * "super long string "],
    ids=["", "random string", "super long string"],
)
def test_token_manager_new_otp(test_token_manager_original_new_otp, token):
    otp = test_token_manager_original_new_otp._new_otp(token)
    assert len(otp) == 128
    assert all(c in string.hexdigits for c in otp)


def test_token_manager_generate_otp(test_token_manager):
    assert test_token_manager.generate_otp(MOCK_TOKEN) == {
        "supported": True,
        "successful": True,
    }


def test_token_manager_generate_otp_fail(test_token_manager, monkeypatch):
    monkeypatch.setattr(test_token_manager.database, "store", mock_exception)
    assert test_token_manager.generate_otp(MOCK_TOKEN) == {
        "supported": True,
        "successful": False,
    }


def test_token_manager_get_token_fail(test_token_manager, monkeypatch):
    monkeypatch.setattr(test_token_manager.database, "pop", mock_exception)
    test_token_manager.generate_otp(MOCK_TOKEN)
    assert test_token_manager.get_token(MOCK_OTP) == None


async def test_token_manager_inject_token_not_in_kwargs(test_token_manager):
    @test_token_manager.inject_token
    async def mock_func(arg1: str, arg2: str):
        return {"arg1": arg1, "arg2": arg2}

    test_token_manager.generate_otp(MOCK_TOKEN)
    result = await mock_func(arg1=MOCK_TOKEN, arg2=MOCK_OTP)
    assert result["arg1"] == MOCK_TOKEN
    assert result["arg2"] == MOCK_OTP


async def test_token_manager_inject_token_replace_otp(test_token_manager):
    @test_token_manager.inject_token
    async def mock_func(request: Request, header: str):
        request_token = None
        header_token = None
        request_header = request.headers.get("authorization", None)
        if request_header and request_header.startswith("Bearer "):
            request_token = request_header.lstrip("Bearer ")
        if header and header.startswith("Bearer "):
            header_token = header.lstrip("Bearer ")
        return {"request_token": request_token, "header_token": header_token}

    test_token_manager.generate_otp(MOCK_TOKEN)
    result = await mock_func(request=MOCK_OTP_REQUEST, header=MOCK_OTP_HEADERS["Authorization"])
    assert result["request_token"] == MOCK_TOKEN
    assert result["header_token"] == MOCK_TOKEN


async def test_token_manager_inject_token_keep_at(test_token_manager):
    @test_token_manager.inject_token
    async def mock_func(request: Request, header: str):
        request_token = None
        header_token = None
        request_header = request.headers.get("authorization", None)
        if request_header and request_header.startswith("Bearer "):
            request_token = request_header.lstrip("Bearer ")
        if header and header.startswith("Bearer "):
            header_token = header.lstrip("Bearer ")
        return {"request_token": request_token, "header_token": header_token}

    test_token_manager.generate_otp(MOCK_TOKEN)
    result = await mock_func(request=MOCK_REQUEST, header=MOCK_HEADERS["Authorization"])
    assert result["request_token"] == MOCK_TOKEN
    assert result["header_token"] == MOCK_TOKEN


@pytest.mark.parametrize("backend", ["sqlite", "sqlitedict"])
def test_token_db_empty(test_token_db):
    mock_otp = "mock_otp"

    assert test_token_db.get(mock_otp) == None
    assert test_token_db.pop(mock_otp) == None


@pytest.mark.parametrize("backend", ["sqlite", "sqlitedict"])
def test_token_db_insert(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    test_token_db.insert(mock_otp, mock_at)
    assert test_token_db.get(mock_otp) == mock_at
    assert test_token_db.get(mock_otp) == mock_at


@pytest.mark.parametrize("backend", ["sqlite", "sqlitedict"])
def test_token_db_remove(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    test_token_db.insert(mock_otp, mock_at)
    test_token_db.remove(mock_otp)
    assert test_token_db.get(mock_otp) == None


@pytest.mark.parametrize("backend", ["sqlite", "sqlitedict"])
def test_token_db_pop(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    test_token_db.insert(mock_otp, mock_at)
    assert test_token_db.pop(mock_otp) == mock_at
    assert test_token_db.get(mock_otp) == None


@pytest.mark.parametrize("backend", ["sqlite", "sqlitedict"])
def test_token_db_store(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    assert test_token_db.store(mock_otp, mock_at) == True
    assert test_token_db.get(mock_otp) == mock_at


@pytest.mark.parametrize("backend", ["sqlite", "sqlitedict"])
def test_token_db_store_twice(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    # test store twice
    assert test_token_db.store(mock_otp, mock_at) == True
    assert test_token_db.store(mock_otp, mock_at) == True
    assert test_token_db.get(mock_otp) == mock_at


@pytest.mark.parametrize("backend", ["sqlite", "sqlitedict"])
def test_token_db_store_collision(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    assert test_token_db.store(mock_otp, mock_at) == True
    assert test_token_db.store(mock_otp, "another at") == False
    assert test_token_db.get(mock_otp) == mock_at

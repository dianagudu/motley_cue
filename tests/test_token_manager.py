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
    build_request,
    mock_exception,
)

DB_BACKENDS = ["memory", "sqlite", "sqlitedict"]


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
    os.chmod(keyfile, 0o400)

    encryption = test_encryption(keyfile)
    assert secret == encryption.decrypt(encryption.encrypt(secret))

    os.remove(keyfile)


@pytest.mark.parametrize("mode", [0o444, 0o440, 0o600 | 0o004, 0o777])
def test_encryption_refuses_keyfile_readable_by_others(test_encryption, mode):
    """A key readable by group or other decrypts every Access Token in the OTP
    database, so loading it must fail loudly rather than silently succeed."""
    keyfile = "tmp_keyfile"
    open(keyfile, "wb").write(Fernet.generate_key())
    os.chmod(keyfile, mode)

    with pytest.raises(Exception) as excinfo:
        _ = test_encryption(keyfile)
    assert "group or other" in str(excinfo.value)

    os.remove(keyfile)


def test_encryption_refuses_symlinked_keyfile(test_encryption, tmp_path):
    """The keyfile is opened O_NOFOLLOW: a symlink at that path was planted by
    someone else, since we only ever create the key with O_EXCL."""
    real_key = tmp_path / "planted.key"
    real_key.write_bytes(Fernet.generate_key())
    real_key.chmod(0o400)
    keyfile = str(tmp_path / "tmp_keyfile")
    os.symlink(real_key, keyfile)

    with pytest.raises(Exception):
        _ = test_encryption(keyfile)


def test_encryption_does_not_adopt_a_pre_created_key(test_encryption, tmp_path):
    """The /tmp attack: a local user plants a key of their choosing before the
    service first starts. create_key must not silently adopt it -- here it is
    left world-readable, which is what makes the planting detectable."""
    keyfile = str(tmp_path / "tmp_keyfile")
    attacker_key = Fernet.generate_key()
    with open(keyfile, "wb") as f:
        f.write(attacker_key)
    os.chmod(keyfile, 0o666)

    with pytest.raises(Exception):
        _ = test_encryption(keyfile)


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


@pytest.mark.parametrize("backend", DB_BACKENDS)
def test_token_db_empty(test_token_db):
    mock_otp = "mock_otp"

    assert test_token_db.get(mock_otp) == None
    assert test_token_db.pop(mock_otp) == None


@pytest.mark.parametrize("backend", DB_BACKENDS)
def test_token_db_insert(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    test_token_db.insert(mock_otp, mock_at)
    assert test_token_db.get(mock_otp) == mock_at
    assert test_token_db.get(mock_otp) == mock_at


@pytest.mark.parametrize("backend", DB_BACKENDS)
def test_token_db_remove(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    test_token_db.insert(mock_otp, mock_at)
    test_token_db.remove(mock_otp)
    assert test_token_db.get(mock_otp) == None


@pytest.mark.parametrize("backend", DB_BACKENDS)
def test_token_db_pop(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    test_token_db.insert(mock_otp, mock_at)
    assert test_token_db.pop(mock_otp) == mock_at
    assert test_token_db.get(mock_otp) == None


@pytest.mark.parametrize("backend", DB_BACKENDS)
def test_token_db_store(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    assert test_token_db.store(mock_otp, mock_at) == True
    assert test_token_db.get(mock_otp) == mock_at


@pytest.mark.parametrize("backend", DB_BACKENDS)
def test_token_db_store_twice(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    # test store twice
    assert test_token_db.store(mock_otp, mock_at) == True
    assert test_token_db.store(mock_otp, mock_at) == True
    assert test_token_db.get(mock_otp) == mock_at


@pytest.mark.parametrize("backend", DB_BACKENDS)
def test_token_db_store_collision(test_token_db):
    mock_otp = "mock_otp"
    mock_at = "mock_at"

    assert test_token_db.store(mock_otp, mock_at) == True
    assert test_token_db.store(mock_otp, "another at") == False
    assert test_token_db.get(mock_otp) == mock_at


### F2: no credential may reach the log, at any level


def test_fingerprint_does_not_contain_the_secret():
    """The point of the helper: what goes in must not come out."""
    from motley_cue.mapper.token_manager import fingerprint

    assert MOCK_TOKEN not in fingerprint(MOCK_TOKEN)


def test_fingerprint_is_stable_and_short():
    """Log lines have to be correlatable across a request, and readable."""
    from motley_cue.mapper.token_manager import fingerprint

    assert fingerprint(MOCK_TOKEN) == fingerprint(MOCK_TOKEN)
    assert len(fingerprint(MOCK_TOKEN)) == 8


def test_fingerprint_distinguishes_a_token_from_its_otp():
    """An OTP is derived from its token, so if the two fingerprinted alike the
    log could no longer tell which of them a line was about."""
    from motley_cue.mapper.token_manager import TokenManager, fingerprint

    assert fingerprint(MOCK_TOKEN) != fingerprint(TokenManager._new_otp(MOCK_TOKEN))


def test_fingerprint_handles_a_missing_secret():
    from motley_cue.mapper.token_manager import fingerprint

    assert fingerprint(None) == "<none>"
    assert fingerprint("") == "<none>"


@pytest.mark.parametrize("backend", DB_BACKENDS)
def test_no_token_or_otp_is_logged_while_storing(test_token_db, caplog):
    """`log_level = DEBUG` is the documented way to diagnose an assurance tier,
    so DEBUG must not put bearer credentials into the journal.

    Run against every backend: each has its own copy of the store/collision log
    lines, so redacting one of them proves nothing about the others.
    """
    import logging

    mock_otp = "mock_otp"

    with caplog.at_level(logging.DEBUG):
        test_token_db.store(mock_otp, MOCK_TOKEN)
        # a second, different token for the same OTP takes the collision path,
        # which logs the token too
        test_token_db.store(mock_otp, "a different token")

    logged = "\n".join(rec.getMessage() for rec in caplog.records)
    assert logged, "expected the store path to log something at DEBUG"
    assert MOCK_TOKEN not in logged
    assert mock_otp not in logged


async def test_no_token_or_otp_is_logged_while_injecting(test_token_manager, caplog):
    """The inject path handles both halves of the mapping at once: it is given
    an OTP and resolves it to an Access Token."""
    import logging

    from motley_cue.mapper.token_manager import TokenManager

    real_otp = TokenManager._new_otp(MOCK_TOKEN)
    test_token_manager.generate_otp(MOCK_TOKEN)

    @test_token_manager.inject_token
    async def mock_func(request: Request):
        return request.headers.get("authorization")

    with caplog.at_level(logging.DEBUG):
        await mock_func(request=build_request(real_otp))

    logged = "\n".join(rec.getMessage() for rec in caplog.records)
    assert MOCK_TOKEN not in logged
    assert real_otp not in logged


@pytest.mark.parametrize(
    "log_level,expected",
    [
        ("DEBUG", "INFO"),
        ("INFO", "INFO"),
        ("WARNING", "WARNING"),
        ("ERROR", "ERROR"),
        ("nonsense", "WARNING"),
    ],
)
def test_flaat_logger_is_clamped_to_info(log_level, expected):
    """flaat logs the raw Access Token at DEBUG, and Config.verbosity hands our
    log_level straight to it -- so DEBUG on our side must not become DEBUG on
    flaat's. Above INFO the level is passed through untouched."""
    import logging

    from motley_cue.mapper import clamp_flaat_logging

    flaat_logger = logging.getLogger("flaat")
    previous = flaat_logger.level
    try:
        clamp_flaat_logging(log_level)
        assert logging.getLevelName(flaat_logger.level) == expected
    finally:
        flaat_logger.setLevel(previous)


### F5: the stored form of an OTP must not itself be a credential


@pytest.mark.parametrize("backend", ["sqlite", "sqlitedict"])
def test_otp_is_not_stored_verbatim(test_token_db):
    """An OTP is the SSH password, so a readable database must not hand out
    working logins. Encrypting only the token column left the key column as a
    complete credential."""
    mock_otp = "mock_otp"
    test_token_db.insert(mock_otp, MOCK_TOKEN)

    with open(f"{test_token_db.backend}_tmp.db", "rb") as f:
        raw = f.read()
    assert mock_otp.encode() not in raw
    assert MOCK_TOKEN.encode() not in raw


@pytest.mark.parametrize("backend", DB_BACKENDS)
def test_lookup_still_works_through_the_digest(test_token_db):
    mock_otp = "mock_otp"
    test_token_db.insert(mock_otp, MOCK_TOKEN)
    assert test_token_db.get(mock_otp) == MOCK_TOKEN
    assert test_token_db.get("some other otp") is None


def test_pop_is_one_time_across_concurrent_workers(tmp_path):
    """ "One-time" is the whole security property of an OTP.

    A plain SELECT opens no transaction in sqlite3's default mode, so two
    gunicorn workers on the same file could both read the row before either
    deleted it, and the same OTP would authenticate twice. The interleaving is
    forced here by making the first worker slow between its read and its delete.
    """
    import threading
    import time

    from motley_cue.mapper import token_manager

    keyfile = str(tmp_path / "key")
    location = str(tmp_path / "tmp.db")
    worker1 = token_manager.SQLiteTokenDB(location, keyfile)
    worker2 = token_manager.SQLiteTokenDB(location, keyfile)
    worker1.insert("mock_otp", MOCK_TOKEN)

    slow_decrypt = worker1.encryption.decrypt

    def decrypt_slowly(secret):
        time.sleep(0.3)  # hold the pop open between its read and its delete
        return slow_decrypt(secret)

    worker1.encryption.decrypt = decrypt_slowly

    results = {}
    thread = threading.Thread(target=lambda: results.__setitem__("w1", worker1.pop("mock_otp")))
    thread.start()
    time.sleep(0.1)  # worker2 arrives while worker1 is mid-pop
    results["w2"] = worker2.pop("mock_otp")
    thread.join()

    assert sorted(results.values(), key=str) == [None, MOCK_TOKEN]


@pytest.mark.parametrize("backend", ["sqlite"])
def test_legacy_cleartext_table_is_dropped(test_token_db, tmp_path):
    """The old table was keyed by the plaintext OTP; leaving it behind would
    leave those credentials on disk."""
    import sqlite3

    with test_token_db.connect() as conn:
        conn.execute("create table if not exists tokenmap (otp text primary key, at text)")
        conn.execute("insert into tokenmap(otp, at) values ('plaintext_otp', 'x')")

    from motley_cue.mapper import token_manager

    token_manager.SQLiteTokenDB("tmp.db", "tmp_keyfile")  # a restart

    with test_token_db.connect() as conn:
        tables = [
            row[0] for row in conn.execute("select name from sqlite_master where type='table'")
        ]
    assert "tokenmap" not in tables
    assert "otpmap" in tables

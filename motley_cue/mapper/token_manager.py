"""
Module for managing one-time tokens and the (long) Access Tokens they are derived from.
"""

from abc import abstractmethod
import os
import stat
from typing import Callable, Optional
import hashlib
import logging
from functools import wraps
import pathlib
import json
import sqlite3
import sqlitedict
from cryptography.fernet import Fernet
from pathlib import Path

from motley_cue.mapper.config import ConfigOTP
from motley_cue.mapper.exceptions import InternalException

logger = logging.getLogger(__name__)


def fingerprint(secret: Optional[str]) -> str:
    """Return a short, stable stand-in for a secret, safe to write to a log.

    Both halves of the OTP mapping are credentials: the Access Token is a bearer
    token at every relying party of its OP, and the OTP is the SSH password --
    `inject_token` exchanges it for the Access Token before authorisation runs.
    Neither belongs in a log that the systemd-journal group can read, that gets
    forwarded to a central collector, and that ends up in backups.

    What the log lines actually need is to be able to follow one token through a
    request, and to tell "this token" from "that token" -- a fingerprint does
    both. A token and its OTP fingerprint differently, so the two stay
    distinguishable in the log.
    """
    if not secret:
        return "<none>"
    return hashlib.sha256(secret.encode()).hexdigest()[:8]


class Encryption:
    """Class for encrypting/decrypting strings using symmetric keys."""

    def __init__(self, keyfile: str) -> None:
        """Initialise Encryption by creating new key and saving it to keyfile
        if it does not exist, and loading the key from keyfile.
        """
        Encryption.create_key(keyfile)
        self.fernet = Encryption.load_fernet(keyfile)

    @staticmethod
    def _vet_keyfile(file_descriptor: int, keyfile: str) -> None:
        """Refuse a key file that someone else could have planted or read.

        This key decrypts every Access Token in the OTP database, so a key an
        attacker was able to write is a key that lets them impersonate every
        user of the service, and a key they could read is the same thing. Both
        are worth refusing to start over -- a service that is down is a much
        smaller problem than one silently using an attacker's key.

        Checks are made against the already-open descriptor, so nothing can be
        swapped between the check and the read.
        """
        info = os.fstat(file_descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise InternalException(
                message=f"Refusing to use the secret key in {keyfile}: not a regular file."
            )
        if info.st_uid != os.geteuid():
            raise InternalException(
                message=(
                    f"Refusing to use the secret key in {keyfile}: it is owned by uid "
                    f"{info.st_uid}, but this service runs as uid {os.geteuid()}. Whoever "
                    "owns this file can read every Access Token in the OTP database."
                )
            )
        if info.st_mode & 0o077:
            raise InternalException(
                message=(
                    f"Refusing to use the secret key in {keyfile}: mode "
                    f"{oct(info.st_mode & 0o777)} grants access to group or other. "
                    f"Fix with: chmod 0400 {keyfile}"
                )
            )

    @staticmethod
    def load_fernet(keyfile: str) -> Fernet:
        """Loads a secret key from keyfile and returns a Fernet object.

        Opened with O_NOFOLLOW and vetted by `_vet_keyfile` before being
        trusted: a symlink is never a key we put there ourselves.
        """
        try:
            file_descriptor = os.open(keyfile, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError as ex:
            logger.error("Could not open secret key in %s: %s", keyfile, ex)
            raise InternalException(message=f"Could not open the secret key in {keyfile}") from ex
        try:
            Encryption._vet_keyfile(file_descriptor, keyfile)
            with os.fdopen(file_descriptor, "rb") as key_file:
                key = key_file.read()
        except InternalException:
            os.close(file_descriptor)
            raise
        except Exception as ex:
            logger.error(
                "Something went wrong when trying to load secret key in %s",
                keyfile,
            )
            raise InternalException(message=f"Could not create secret key in {keyfile}") from ex
        try:
            return Fernet(key)
        except Exception as ex:
            logger.error(
                "Something went wrong when trying to load secret key in %s",
                keyfile,
            )
            raise InternalException(message=f"Could not create secret key in {keyfile}") from ex

    @staticmethod
    def create_key(keyfile: str) -> None:
        """Creates a fresh Fernet (secret) key and saves it to keyfile,
        only if key does not already exist. Sets appropriate permissions on keyfile.

        O_EXCL|O_NOFOLLOW means we either create the file or lose the race --
        never follow a symlink someone else planted at this path. open(2) applies
        the mode itself, so unlike a chmod after the write there is no moment at
        which the key sits on disk at the process umask.
        """
        try:
            Path(keyfile).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            file_descriptor = os.open(
                keyfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o400
            )
        except FileExistsError:
            logger.debug("Key already exists in %s, nothing to do here.", keyfile)
            return
        except Exception as ex:
            logger.error(
                "Something went wrong when trying to create secret key in %s",
                keyfile,
            )
            raise InternalException(message=f"Could not create secret key in {keyfile}") from ex
        try:
            # belt and braces: the umask could have cleared bits from the mode above
            os.fchmod(file_descriptor, 0o400)
            with os.fdopen(file_descriptor, "wb") as key_file:
                key_file.write(Fernet.generate_key())
            logger.debug("Created secret key for encryption and saved it to %s.", keyfile)
        except Exception as ex:
            logger.error(
                "Something went wrong when trying to create secret key in %s",
                keyfile,
            )
            raise InternalException(message=f"Could not create secret key in {keyfile}") from ex

    def encrypt(self, secret: str) -> str:
        """Encrypt secret using Fernet key"""
        return self.fernet.encrypt(secret.encode()).decode()

    def decrypt(self, secret: str) -> str:
        """Decrypt secret using Fernet key"""
        return self.fernet.decrypt(secret.encode()).decode()


class TokenDB:
    """Generic database for mapping of short-lived / one-time-use tokens to access tokens
    All methods must be implemented: pop, store, get, insert, delete.
    """

    backend = "generic"

    # Bumped from the original "tokenmap", which was keyed by the plaintext OTP.
    # Creating a new table rather than migrating drops those rows, which is the
    # point: they are the cleartext credentials this change exists to remove.
    # OTPs are one-time and short-lived, so the cost is that anyone holding an
    # unused one calls /user/generate_otp again.
    table = "otpmap"
    legacy_table = "tokenmap"

    def rename_location(self, location) -> str:
        """Add prefix to filename where database is stored, to differentiate between backends."""
        new_location = pathlib.Path(location)
        return str(new_location.parent.joinpath(f"{self.backend}_{new_location.name}"))

    @staticmethod
    def key(otp: str) -> str:
        """Return the lookup key to store an OTP under.

        Not the OTP itself: an OTP *is* a credential -- `inject_token` exchanges
        it for the Access Token before authorisation runs, which makes it the
        SSH password -- so storing it verbatim as the primary key handed anyone
        who could read the database a working login for every user with a live
        OTP. Encrypting the `at` column bought nothing against exactly the
        disclosure it was meant for: a stray copy, a backup, a dropped file.

        A digest is enough because lookup only ever needs equality, and it is
        one-way, so the stored form is no longer a credential.
        """
        return hashlib.sha256(otp.encode()).hexdigest()

    @abstractmethod
    def pop(self, otp: str) -> Optional[str]:
        """Implement one-time logic by removing mapping after get.
        Return None when otp not in db.
        """

    @abstractmethod
    def store(self, otp: str, token: str) -> bool:
        """Do collision checking before inserting mapping to DB.
        Return True on successful insert. If mapping already existed,
        insert is also considered successful.
        Return False on collision.
        """

    @abstractmethod
    def get(self, otp: str) -> Optional[str]:
        """Retrieve access token mapped to given one-time token from db.
        Return None when otp not in db.
        """

    @abstractmethod
    def remove(self, otp: str) -> None:
        """Remove mapping for given one-time token from db.
        Undefined behaviour when otp not in db.
        """

    @abstractmethod
    def insert(self, otp: str, token: str) -> None:
        """Insert mapping between given one-time token and access token to db.
        Undefined behaviour when otp already in db.
        """


class SQLiteTokenDB(TokenDB):
    """SQLite-based DB for mapping one-time tokens to access tokens"""

    backend = "sqlite"

    def __init__(self, location: str, keyfile: str) -> None:
        self.encryption = Encryption(keyfile)
        # new db connection for location (does not need to exist)
        db_name = self.rename_location(location)
        Path(db_name).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.__db_name = db_name
        with self.connect() as conn:  # con.commit() is called automatically afterwards on success
            # create table
            conn.execute(f"create table if not exists {self.table} (otp text primary key, at text)")
            # and take the cleartext OTPs of any previous version off the disk
            conn.execute(f"drop table if exists {self.legacy_table}")

    def connect(self) -> sqlite3.Connection:
        """Connect to DB and return Connection object.

        In conjunction with the with statement, this will automatically connect to the db,
        execute the code in the with block, commit the changes to the db and close the connection.
        This allows for concurrency (e.g. when using gunicorn with multiple processes), as the
        connection is closed after the with block, and mitigates errors such as "database is locked".
        """
        return sqlite3.connect(self.__db_name)

    def pop(self, otp: str) -> Optional[str]:
        """Override pop with db stransactions.

        The select and the delete run inside one write transaction, because
        "one-time" is the entire security property of an OTP. A plain SELECT
        starts no transaction in sqlite3's default mode, so with gunicorn
        running several workers against the same file, two requests could both
        read the row before either deleted it and the same OTP would
        authenticate twice.

        BEGIN IMMEDIATE rather than RETURNING: RETURNING needs SQLite 3.35, and
        rockylinux-8 -- a target distribution -- ships 3.26.
        """
        sql_get = f"select at from {self.table} where otp=?"
        sql_del = f"delete from {self.table} where otp=?"
        token = None
        with self.connect() as conn:
            conn.execute("begin immediate")
            result = conn.execute(sql_get, [self.key(otp)]).fetchall()
            if len(result) == 0:
                return None
            if len(result) > 1:
                logger.warning("Multiple entries found in token db for OTP: %s", fingerprint(otp))
            token = self.encryption.decrypt(result[0][0])
            conn.execute(sql_del, [self.key(otp)])
        return token

    def store(self, otp: str, token: str) -> bool:
        """Override store with db transactions"""
        sql_get = f"select at from {self.table} where otp=?"
        sql_insert = f"insert into {self.table}(otp, at) values (?,?)"
        with self.connect() as conn:
            result = conn.execute(sql_get, [self.key(otp)]).fetchall()
            if len(result) > 0:  # if already in db
                stored_token = self.encryption.decrypt(result[0][0])
                if stored_token == token:  # for the same token
                    logger.debug("OTP already exists for token %s", fingerprint(token))
                    return True
                # else:  # for another token => collision
                logger.debug(
                    "Collision error: OTP for token %s collides with OTP for another token",
                    fingerprint(token),
                )
                return False
            # when not found in db, insert new mapping; only encrypt access token
            logger.debug("Storing OTP [%s] for token [%s]", fingerprint(otp), fingerprint(token))
            conn.execute(
                sql_insert,
                (self.key(otp), self.encryption.encrypt(token)),
            )
        return True

    def get(self, otp: str) -> Optional[str]:
        sql_get = f"select at from {self.table} where otp=?"
        with self.connect() as conn:
            result = conn.execute(sql_get, [self.key(otp)]).fetchall()
            if len(result) == 0:
                return None
            if len(result) > 1:
                logger.warning("Multiple entries found in token db for OTP: %s", fingerprint(otp))
            return self.encryption.decrypt(result[0][0])

    def remove(self, otp: str) -> None:
        sql_del = f"delete from {self.table} where otp=?"
        with self.connect() as conn:
            conn.execute(sql_del, [self.key(otp)])

    def insert(self, otp: str, token: str) -> None:
        sql_insert = f"insert into {self.table}(otp, at) values (?,?)"
        with self.connect() as conn:
            conn.execute(sql_insert, (self.key(otp), self.encryption.encrypt(token)))


class MemorySQLiteTokenDB(TokenDB):
    """In-memory SQLite-based DB for mapping one-time tokens to access tokens"""

    backend = "memory"

    def __init__(self, keyfile: str) -> None:
        self.encryption = Encryption(keyfile)
        # create connection to in-memory db once, so that it persists during the lifetime of the MemorySQLiteTokenDB object
        self.connection = sqlite3.connect("file::memory:?cache=shared", uri=True)
        # create table
        self.connection.cursor().execute(
            f"create table if not exists {self.table} (otp text primary key, at text)"
        )

    def close(self):
        """Close connection to in-memory db."""
        self.connection.close()

    def pop(self, otp: str) -> Optional[str]:
        """Override pop with db stransactions"""
        sql_get = f"select at from {self.table} where otp=?"
        sql_del = f"delete from {self.table} where otp=?"
        token = None
        result = self.connection.cursor().execute(sql_get, [self.key(otp)]).fetchall()
        if len(result) == 0:
            return None
        if len(result) > 1:
            logger.warning("Multiple entries found in token db for OTP: %s", fingerprint(otp))
        token = self.encryption.decrypt(result[0][0])
        self.connection.cursor().execute(sql_del, [self.key(otp)])
        return token

    def store(self, otp: str, token: str) -> bool:
        """Override store with db transactions"""
        sql_get = f"select at from {self.table} where otp=?"
        sql_insert = f"insert into {self.table}(otp, at) values (?,?)"
        result = self.connection.cursor().execute(sql_get, [self.key(otp)]).fetchall()
        if len(result) > 0:  # if already in db
            stored_token = self.encryption.decrypt(result[0][0])
            if stored_token == token:  # for the same token
                logger.debug("OTP already exists for token %s", fingerprint(token))
                return True
            # else:  # for another token => collision
            logger.debug(
                "Collision error: OTP for token %s collides with OTP for another token",
                fingerprint(token),
            )
            return False
        # when not found in db, insert new mapping; only encrypt access token
        logger.debug("Storing OTP [%s] for token [%s]", fingerprint(otp), fingerprint(token))
        self.connection.cursor().execute(
            sql_insert,
            (self.key(otp), self.encryption.encrypt(token)),
        )
        return True

    def get(self, otp: str) -> Optional[str]:
        sql_get = f"select at from {self.table} where otp=?"
        result = self.connection.cursor().execute(sql_get, [self.key(otp)]).fetchall()
        if len(result) == 0:
            return None
        if len(result) > 1:
            logger.warning("Multiple entries found in token db for OTP: %s", fingerprint(otp))
        return self.encryption.decrypt(result[0][0])

    def remove(self, otp: str) -> None:
        sql_del = f"delete from {self.table} where otp=?"
        self.connection.cursor().execute(sql_del, [self.key(otp)])

    def insert(self, otp: str, token: str) -> None:
        sql_insert = f"insert into {self.table}(otp, at) values (?,?)"
        self.connection.cursor().execute(
            sql_insert, (self.key(otp), self.encryption.encrypt(token))
        )


class SQLiteDictTokenDB(TokenDB):
    """SQLiteDict-based DB for mapping one-time tokens to access tokens"""

    backend = "sqlitedict"

    def __init__(self, location: str, keyfile: str) -> None:
        self.encryption = Encryption(keyfile)
        db_name = self.rename_location(location)
        Path(db_name).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.database = sqlitedict.SqliteDict(
            db_name,
            tablename=self.table,
            flag="c",
            encode=self._encrypted_encode,
            decode=self._encrypted_decode,
        )

    def _encrypted_encode(self, obj):
        return sqlite3.Binary(self.encryption.encrypt(json.dumps(obj)).encode("utf-8"))

    def _encrypted_decode(self, obj):
        return json.loads(self.encryption.decrypt(obj.decode("utf-8")))

    def pop(self, otp: str) -> Optional[str]:
        """NOTE: unlike the `sqlite` backend, this cannot make the read and the
        delete one transaction -- sqlitedict exposes a mapping, and its
        __delitem__ is a separate statement queued on its writer thread. Across
        several gunicorn workers on one file, two requests can therefore both
        consume the same OTP. Use the `sqlite` backend where that matters.
        """
        token = None
        if self.key(otp) in self.database:
            token = str(self.database[self.key(otp)])
            del self.database[self.key(otp)]
        self.database.commit()
        return token

    def store(self, otp: str, token: str) -> bool:
        stored_token = None
        success = False
        if self.key(otp) in self.database:
            stored_token = str(self.database[self.key(otp)])
        if not stored_token:
            logger.debug("Storing OTP [%s] for token [%s]", fingerprint(otp), fingerprint(token))
            self.database[self.key(otp)] = token
            success = True
        elif stored_token == token:
            logger.debug("OTP already exists for token %s", fingerprint(token))
            success = True
        else:
            logger.debug(
                "Collision error: OTP for token %s collides with OTP for another token",
                fingerprint(token),
            )
            success = False
        self.database.commit()
        return success

    def get(self, otp: str) -> Optional[str]:
        token = None
        if self.key(otp) in self.database:
            token = str(self.database[self.key(otp)])
        self.database.commit()
        return token

    def remove(self, otp: str) -> None:
        del self.database[self.key(otp)]
        self.database.commit()

    def insert(self, otp: str, token: str) -> None:
        self.database[self.key(otp)] = token
        self.database.commit()


class TokenManager:
    """Class to manage short lived & short tokens:

    - useful for long tokens (>1k)
    - maps ATs to OTPs (shorter, short-lived tokens)
    - generates OTP by hashing the AT
    - stores mapping OTP <-> AT in a secure db
        - this is done on /user/generate_otp
    - use OTP as ssh password
        - on /verify_user, OTP is translated to AT and then
          we go forward with authorisation & usual verification
    - security: one-time use (remove mapping once it is used)
    """

    def __init__(self, otp_config: ConfigOTP) -> None:
        """Any DB-related initialisations"""
        if otp_config.backend == "sqlite":
            self.__db = SQLiteTokenDB(otp_config.db_location, otp_config.keyfile)
        elif otp_config.backend == "sqlitedict":
            self.__db = SQLiteDictTokenDB(otp_config.db_location, otp_config.keyfile)
        elif otp_config.backend == "memory":
            self.__db = MemorySQLiteTokenDB(otp_config.keyfile)
        else:
            raise InternalException(f"Unknown backend for token manager: {otp_config.backend}")

    @property
    def database(self):
        """Return TokenDB object"""
        return self.__db

    @classmethod
    def from_config(cls, otp_config: ConfigOTP):
        """Load TokenManager from given config object"""
        if otp_config.use_otp:
            return cls(otp_config)
        return None

    @staticmethod
    def _new_otp(token: str) -> str:
        """Create a new OTP by hashing given token."""
        return hashlib.sha512(bytearray(token, "ascii")).hexdigest()

    def get_token(self, otp: str) -> Optional[str]:
        """Retrieve the token associated to this OTP from token DB."""
        try:
            return self.database.pop(otp)
        except Exception as ex:  # pylint: disable=broad-except
            logger.debug(
                "Failed to get or remove token mapping for otp %s: %s", fingerprint(otp), ex
            )
            return None

    def generate_otp(self, token: str) -> dict:
        """Generate and store a new OTP for given token."""
        try:
            otp = TokenManager._new_otp(token)
            success = self.database.store(otp, token)
        except Exception as ex:  # pylint: disable=broad-except
            logger.debug(
                "Failed to create or store an otp for token [%s]: %s",
                fingerprint(token),
                ex,
            )
            success = False
        return {"supported": True, "successful": success}

    def inject_token(self, func: Callable) -> Callable:
        """Decorator that replaces the given token (OTP) with its corresponding AT.
        Only if given token is found in OTP db.
        Otherwise pass token through as is, and it will be treated like an AT.
        """

        def _get_token_from_kwargs(kwargs: dict):
            """Get token from function kwargs, either present in header or request header"""
            header = None
            if "header" in kwargs:  # pragma: no cover
                header = kwargs["header"]
            if "request" in kwargs:
                header = kwargs["request"].headers.get("authorization", None)
            if header and header.startswith("Bearer "):
                return header[len("Bearer ") :]
            return None

        def _replace_token_in_kwargs(kwargs: dict, token: str) -> dict:
            """If present in kwargs, replace bearer token in authorization request header
            with given token.
            """
            if "header" not in kwargs and "request" not in kwargs:
                logger.warning("header or request not in kwargs")
                return kwargs

            if "header" in kwargs and kwargs["header"].startswith("Bearer "):
                kwargs["header"] = f"Bearer {token}"
            if "request" in kwargs:
                authz_header = kwargs["request"].headers.get("authorization", None)
                if authz_header and authz_header.startswith("Bearer "):
                    new_headers = kwargs["request"].headers.mutablecopy()
                    new_headers["authorization"] = f"Bearer {token}"
                    kwargs["request"]._headers = new_headers  # pylint: disable=protected-access
                    kwargs["request"].scope.update(headers=new_headers.raw)
            return kwargs

        @wraps(func)
        async def wrapper(*args, **kwargs):
            otp = _get_token_from_kwargs(kwargs)
            if otp:
                logger.debug("Found token in kwargs: %s", fingerprint(otp))
                access_token = self.get_token(otp)
                if access_token:
                    logger.debug("OTP %s found in token DB", fingerprint(otp))
                    kwargs = _replace_token_in_kwargs(kwargs, access_token)
                    logger.debug(
                        "Injected Access Token %s corresponding to given OTP %s",
                        fingerprint(access_token),
                        fingerprint(otp),
                    )
            return await func(*args, **kwargs)

        return wrapper

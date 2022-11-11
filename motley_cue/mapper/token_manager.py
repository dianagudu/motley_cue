"""
Module for managing one-time tokens and the (long) Access Tokens they are derived from.
"""
from abc import abstractmethod
import os
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

from .config import ConfigOTP
from .exceptions import InternalException

logger = logging.getLogger(__name__)


class Encryption:
    """Class for encrypting/decrypting strings using symmetric keys."""

    def __init__(self, keyfile: str) -> None:
        """Initialise Encryption by creating new key and saving it to keyfile
        if it does not exist, and loading the key from keyfile.
        """
        Encryption.create_key(keyfile)
        self.fernet = Encryption.load_fernet(keyfile)

    @staticmethod
    def load_fernet(keyfile: str) -> Fernet:
        """Loads a secret key from keyfile and returns a Fernet object."""
        try:
            key = open(keyfile, "rb").read()  # pylint: disable=consider-using-with
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
        """
        try:
            key = Fernet.generate_key()
            Path(keyfile).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            open(keyfile, "xb").write(key)  # pylint: disable=consider-using-with
            os.chmod(keyfile, 0o400)
            logger.debug("Created secret key for encryption and saved it to %s.", keyfile)
        except FileExistsError:
            logger.debug("Key already exists in %s, nothing to do here.", keyfile)
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

    def rename_location(self, location) -> str:
        """Add prefix to filename where database is stored, to differentiate between backends."""
        new_location = pathlib.Path(location)
        return str(new_location.parent.joinpath(f"{self.backend}_{new_location.name}"))

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
        self.connection = sqlite3.connect(db_name)
        with self.connection:  # con.commit() is called automatically afterwards on success
            # create table
            self.connection.execute(
                """create table if not exists tokenmap
                        (otp text primary key, at text)"""
            )

    def pop(self, otp: str) -> Optional[str]:
        """Override pop with db stransactions"""
        sql_get = "select at from tokenmap where otp=?"
        sql_del = "delete from tokenmap where otp=?"
        token = None
        with self.connection:
            result = self.connection.execute(sql_get, [otp]).fetchall()
            if len(result) == 0:
                return None
            if len(result) > 1:
                logger.warning("Multiple entries found in token db for OTP: %s", otp)
            token = self.encryption.decrypt(result[0][0])
            self.connection.execute(sql_del, [otp])
        return token

    def store(self, otp: str, token: str) -> bool:
        """Override store with db transactions"""
        sql_get = "select at from tokenmap where otp=?"
        sql_insert = "insert into tokenmap(otp, at) values (?,?)"
        with self.connection:
            result = self.connection.execute(sql_get, [otp]).fetchall()
            if len(result) > 0:  # if already in db
                stored_token = self.encryption.decrypt(result[0][0])
                if stored_token == token:  # for the same token
                    logger.debug("OTP already exists for token %s", token)
                    return True
                # else:  # for another token => collision
                logger.debug(
                    "Collision error: OTP for token %s collides with OTP for another token",
                    token,
                )
                return False
            # when not found in db, insert new mapping; only encrypt access token
            logger.debug("Storing OTP [%s] for token [%s]", otp, token)
            self.connection.execute(
                sql_insert,
                (otp, self.encryption.encrypt(token)),
            )
        return True

    def get(self, otp: str) -> Optional[str]:
        sql_get = "select at from tokenmap where otp=?"
        with self.connection:
            result = self.connection.execute(sql_get, [otp]).fetchall()
            if len(result) == 0:
                return None
            if len(result) > 1:
                logger.warning("Multiple entries found in token db for OTP: %s", otp)
            return self.encryption.decrypt(result[0][0])

    def remove(self, otp: str) -> None:
        sql_del = "delete from tokenmap where otp=?"
        with self.connection:
            self.connection.execute(sql_del, [otp])

    def insert(self, otp: str, token: str) -> None:
        sql_insert = "insert into tokenmap(otp, at) values (?,?)"
        with self.connection:
            self.connection.execute(sql_insert, (otp, self.encryption.encrypt(token)))


class SQLiteDictTokenDB(TokenDB):
    """SQLiteDict-based DB for mapping one-time tokens to access tokens"""

    backend = "sqlitedict"

    def __init__(self, location: str, keyfile: str) -> None:
        self.encryption = Encryption(keyfile)
        db_name = self.rename_location(location)
        Path(db_name).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.database = sqlitedict.SqliteDict(
            db_name,
            tablename="tokenmap",
            flag="c",
            encode=self._encrypted_encode,
            decode=self._encrypted_decode,
        )

    def _encrypted_encode(self, obj):
        return self.encryption.encrypt(json.dumps(obj))

    def _encrypted_decode(self, obj):
        return json.loads(self.encryption.decrypt(obj))

    def pop(self, otp: str) -> Optional[str]:
        token = None
        if otp in self.database:
            token = str(self.database[otp])
            del self.database[otp]
        self.database.commit()
        return token

    def store(self, otp: str, token: str) -> bool:
        stored_token = None
        success = False
        if otp in self.database:
            stored_token = str(self.database[otp])
        if not stored_token:
            logger.debug("Storing OTP [%s] for token [%s]", otp, token)
            self.database[otp] = token
            success = True
        elif stored_token == token:
            logger.debug("OTP already exists for token %s", token)
            success = True
        else:
            logger.debug(
                "Collision error: OTP for token %s collides with OTP for another token",
                token,
            )
            success = False
        self.database.commit()
        return success

    def get(self, otp: str) -> Optional[str]:
        token = None
        if otp in self.database:
            token = str(self.database[otp])
        self.database.commit()
        return token

    def remove(self, otp: str) -> None:
        del self.database[otp]
        self.database.commit()

    def insert(self, otp: str, token: str) -> None:
        self.database[otp] = token
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
            logger.debug("Failed to get or remove token mapping for otp %s: %s", otp, ex)
            return None

    def generate_otp(self, token: str) -> dict:
        """Generate and store a new OTP for given token."""
        try:
            otp = TokenManager._new_otp(token)
            success = self.database.store(otp, token)
        except Exception as ex:  # pylint: disable=broad-except
            logger.debug(
                "Failed to create or store an otp for token [%s]: %s",
                token,
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
                logger.debug("Found token in kwargs: %s", otp)
                access_token = self.get_token(otp)
                if access_token:
                    logger.debug("OTP %s found in token DB", otp)
                    kwargs = _replace_token_in_kwargs(kwargs, access_token)
                    logger.debug(
                        "Injected Access Token %s corresponding to given OTP %s",
                        access_token,
                        otp,
                    )
            return await func(*args, **kwargs)

        return wrapper

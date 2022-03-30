from typing import Callable, Optional
import hashlib
import logging
from functools import wraps
import pathlib
from sqlcipher3 import dbapi2 as sqlcipher
import shelve

from .config import OTPConfig

logger = logging.getLogger(__name__)


class TokenDB:
    """Generic database for mapping of short-lived / one-time-use tokens to access tokens
    All methods must be implemented: pop, store, get, insert, delete.
    """

    backend = "generic"

    def rename_location(self, location) -> str:
        p = pathlib.Path(location)
        return str(p.parent.joinpath(f"{self.backend}_{p.name}"))

    def pop(self, otp: str) -> Optional[str]:
        """Implement one-time logic by removing mapping after get."""
        return None

    def store(self, otp: str, token: str) -> bool:
        """Do collision checking before inserting mapping to DB.
        Return True on successful insert. If mapping already existed,
        insert is also considered successful.
        """
        return False

    def get(self, otp: str) -> Optional[str]:
        """Retrieve access token mapped to given one-time token from db."""
        return None

    def delete(self, otp: str) -> bool:
        """Remove mapping for given one-time token from db."""
        return False

    def insert(self, otp: str, token: str) -> bool:
        """Insert mapping between given one-time token and access token to db."""
        return False


class SQLiteTokenDB(TokenDB):
    """SQLite-based DB for mapping one-time tokens to access tokens"""

    backend = "sqlite"

    def __init__(self, location: str, password: str) -> None:
        # new db connection for location (does not need to exist)
        self.connection = sqlcipher.connect(self.rename_location(location))
        self.connection.execute(f'pragma key="{password}"')
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
            token = result[0][0]
            self.connection.execute(sql_del, [otp])
        return token

    def store(self, otp: str, token: str) -> bool:
        """Override store with db transactions"""
        sql_get = "select at from tokenmap where otp=?"
        sql_insert = "insert into tokenmap(otp, at) values (?,?)"
        with self.connection:
            # look for otp in db
            result = self.connection.execute(sql_get, [otp]).fetchall()
            # if already in db
            if len(result) > 0:
                stored_token = result[0][0]
                # for the same token
                if stored_token == token:
                    logger.debug("OTP already exists for token %s", token)
                    return True
                else:  # for another token => collision
                    logger.debug(
                        "Collision error: OTP for token %s collides with OTP for another token",
                        token,
                    )
                    return False
            # when not found in db, insert new mapping
            self.connection.execute(sql_insert, (otp, token))
        return True

    def get(self, otp: str) -> Optional[str]:
        sql_get = "select at from tokenmap where otp=?"
        with self.connection:
            result = self.connection.execute(sql_get, [otp]).fetchall()
        if len(result) == 0:
            return None
        if len(result) > 1:
            logger.warning("Multiple entries found in token db for OTP: %s", otp)
        return result[0][0]

    def delete(self, otp: str) -> bool:
        sql_del = "delete from tokenmap where otp=?"
        with self.connection:
            self.connection.execute(sql_del, [otp])
        return True

    def insert(self, otp: str, token: str) -> bool:
        sql_insert = "insert into tokenmap(otp, at) values (?,?)"
        with self.connection:
            self.connection.execute(sql_insert, (otp, token))
        return True


class ShelveTokenDB(TokenDB):
    """Shelve-based DB for mapping one-time tokens to access tokens"""

    backend = "shelve"

    def __init__(self, location: str) -> None:
        self.__location = self.rename_location(location)

    def _open_db(self) -> shelve.Shelf:
        return shelve.open(self.__location, flag="c")

    def _close_db(self, db: shelve.Shelf):
        db.close()

    def pop(self, otp: str) -> Optional[str]:
        token = None
        db = self._open_db()
        if otp in db:
            token = str(db[otp])
            del db[otp]
        self._close_db(db)
        return token

    def store(self, otp: str, token: str) -> bool:
        stored_token = None
        success = False
        db = self._open_db()
        if otp in db:
            stored_token = str(db[otp])
        if not stored_token:
            logger.debug("Storing OTP [%s] for token [%s]", otp, token)
            db[otp] = token
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
        self._close_db(db)
        return success

    def get(self, otp: str) -> Optional[str]:
        token = None
        db = self._open_db()
        if otp in db:
            token = str(db[otp])
        self._close_db(db)
        return token

    def delete(self, otp: str) -> bool:
        db = self._open_db()
        del db[otp]
        self._close_db(db)
        return True

    def insert(self, otp: str, token: str) -> bool:
        db = self._open_db()
        db[otp] = token
        self._close_db(db)
        return True


class TokenManager:
    """Class to manage short lived & short tokens:

    - useful for long tokens (>1k)
    - maps ATs to OTPs (shorter, short-lived tokens)
    - generates OTP by hashing the AT
    - stores mapping OTP <-> AT in a secure db (or in memory??)
        - this is done on /user/generate_otp
    - use OTP as ssh password
        - on /verify_user, OTP is translated to AT and then we go forward with authorisation & usual verification
    - security:
        - either one-time use (remove mapping once it is used)
        - or expiration after a certain time
    """

    def __init__(self, otp_config: OTPConfig) -> None:
        """Any DB-related initialisations"""
        if otp_config.backend == "sqlite":
            self.__db = SQLiteTokenDB(otp_config.db_location, otp_config.password)
        elif otp_config.backend == "shelve":
            self.__db = ShelveTokenDB(otp_config.db_location)

    @classmethod
    def from_config(cls, otp_config: OTPConfig):
        if otp_config.use_otp:
            return cls(otp_config)
        return None

    def _new_otp(self, token: str) -> str:
        """Create a new OTP by hashing given token."""
        return hashlib.sha512(bytearray(token, "ascii")).hexdigest()

    def get_token(self, otp: str) -> Optional[str]:
        """Retrieve the token associated to this OTP from token DB."""
        try:
            return self.__db.pop(otp)
        except Exception as e:
            logger.debug("Failed to get or remove token mapping for otp %s: %s", otp, e)
            return None

    def generate_otp(self, token: str) -> dict:
        """Generate and store a new OTP for given token."""
        try:
            otp = self._new_otp(token)
            success = self.__db.store(otp, token)
        except Exception as e:
            logger.debug(
                "Failed to create or store an otp for token [%s]: %s",
                token,
                e,
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
                return header.lstrip("Bearer ")
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
                    kwargs["request"]._headers = new_headers

            return kwargs

        @wraps(func)
        async def wrapper(*args, **kwargs):
            otp = _get_token_from_kwargs(kwargs)
            if otp:
                logger.debug("Found token in kwargs: %s", otp)
                at = self.get_token(otp)
                if at:
                    logger.debug("OTP %s found in token DB", otp)
                    kwargs = _replace_token_in_kwargs(kwargs, at)
                    logger.debug(
                        "Injected Access Token %s corresponding to given OTP %s",
                        at,
                        otp,
                    )
            return await func(*args, **kwargs)

        return wrapper

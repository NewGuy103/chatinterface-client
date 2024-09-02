import sqlite3
import asyncio
import os

import uuid
import logging
import keyring

from contextlib import contextmanager
from functools import wraps
from ..config import dirs, simple_log_setup

logger: logging.Logger = simple_log_setup()


class KeyringManager:
    def __init__(self) -> None:
        self.__setup_done: bool = False
        self.SERVICE_NAME: str = 'chatinterface'

        self.base_dir: str = dirs.user_data_dir
        self.config_file: str = os.path.join(self.base_dir, "keyring.sqlite")

    @contextmanager
    def transaction(self):
        try:
            cursor: sqlite3.Cursor = self.db.cursor()
        except sqlite3.Error:
            logger.exception("Cursor could not be created:")
            raise

        try:
            cursor.execute("BEGIN TRANSACTION;")
            with self.db:
                yield cursor

            self.db.commit()
        except sqlite3.Error:
            logger.exception("Could not commit transaction to keyring configuration file:")
            self.db.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def async_threaded(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.to_thread(func, *args, **kwargs)
        
        return wrapper

    @async_threaded
    def setup(self):
        self.db: sqlite3.Connection = sqlite3.connect(self.config_file, check_same_thread=False)
        with self.transaction() as cursor:
            cursor.executescript("""
                PRAGMA foreign_keys = ON;
                PRAGMA autovacuum = FULL;

                CREATE TABLE IF NOT EXISTS hostnames (
                    hostname TEXT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS keys (
                    key_uuid TEXT PRIMARY KEY,
                    hostname TEXT,

                    username TEXT,
                    FOREIGN KEY (hostname) REFERENCES hostnames(hostname)
                        ON DELETE CASCADE
                        ON UPDATE CASCADE
                );
            """)
        
        self.__setup_done: bool = True

    @async_threaded
    def set_password(self, hostname: str, username: str, password: str) -> int:
        if not self.__setup_done:
            raise RuntimeError("run setup() before using this class")

        if not isinstance(hostname, str):
            raise TypeError("hostname is not a string")
        
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        if not isinstance(password, str):
            raise TypeError("password is not a string")

        key_id: str = str(uuid.uuid4())
        with self.transaction() as cursor:
            cursor.execute("SELECT hostname FROM hostnames WHERE hostname=?", [hostname])
            hostname_exists: tuple[str] | None = cursor.fetchone()

            if not hostname_exists:
                cursor.execute("INSERT INTO hostnames (hostname) VALUES (?)", [hostname])

            cursor.execute("""
                INSERT INTO keys (key_uuid, hostname, username)
                VALUES (?, ?, ?)
            """, [key_id, hostname, username])
        
        keyring.set_password(self.SERVICE_NAME, key_id, password)
        return 0
    
    @async_threaded
    def get_password(self, hostname: str, username: str) -> str:
        if not self.__setup_done:
            raise RuntimeError("run setup() before using this class")

        if not isinstance(hostname, str):
            raise TypeError("hostname is not a string")

        if not isinstance(username, str):
            raise TypeError("username is not a string")

        with self.transaction() as cursor:
            cursor.execute("SELECT hostname FROM hostnames WHERE hostname=?", [hostname])
            hostname_exists: tuple[str] | None = cursor.fetchone()

            if not hostname_exists:
                return "INVALID_HOSTNAME"
            
            cursor.execute("""
                SELECT key_uuid FROM keys
                WHERE hostname=? AND username=?
            """, [hostname, username])
            key_data: tuple[str] | None = cursor.fetchone()

        if not key_data:
            return "NO_KEYS"

        key_id: str = key_data[0]
        return keyring.get_password(self.SERVICE_NAME, key_id)

    @async_threaded
    def delete_password(self, hostname: str, username: str) -> int | str:
        if not self.__setup_done:
            raise RuntimeError("run setup() before using this class")

        if not isinstance(hostname, str):
            raise TypeError("hostname is not a string")
        
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        with self.transaction() as cursor:
            cursor.execute("SELECT hostname FROM hostnames WHERE hostname=?", [hostname])
            hostname_exists: tuple[str] | None = cursor.fetchone()

            if not hostname_exists:
                return "INVALID_HOSTNAME"

            cursor.execute("""
                SELECT key_uuid FROM keys
                WHERE hostname=? AND username=?
            """, [hostname, username])
            key_data: tuple[str] | None = cursor.fetchone()

            if not key_data:
                return "NO_KEYS"

            key_id: str = key_data[0]
            cursor.execute("DELETE FROM keys WHERE key_uuid=?", [key_id])

        keyring.delete_password(self.SERVICE_NAME, key_id)
        return 0

    @async_threaded
    def show_users(self) -> list[tuple[str, str]] | str:
        if not self.__setup_done:
            raise RuntimeError("run setup() before using this class")

        with self.transaction() as cursor:
            cursor.execute("SELECT hostname, username FROM keys")
            key_data: list[tuple[str, str]] | None = cursor.fetchall()

            if not key_data:
                return "NO_USERS"
        
        return key_data

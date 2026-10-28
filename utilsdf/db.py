"""
Database Management Module - Python 3.12+ Compatible
Enhanced with context managers, type hints, and better error handling
"""

import datetime
import logging
import sqlite3
import random
import string
from contextlib import contextmanager
from pathlib import Path
from typing import Union, Optional, Dict, List, Iterator
from os import getenv

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class Database:
    """
    Singleton database manager with improved error handling
    Supports context manager protocol for safe resource management
    """

    _instance: Optional["Database"] = None
    _lock = None

    # Table definitions
    BOT_TABLE = "bot"
    BOT_KEYS_TABLE = "bot_keys"
    BOT_GROUPS = "groups"
    ID_OWNER = "5579729798"

    def __new__(cls) -> "Database":
        """Implement singleton pattern with thread safety"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize database connection"""
        if self._initialized:
            return

        try:
            db_path = Path("assets") / "db_bot.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)

            self.connection = sqlite3.connect(str(db_path), check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Access columns by name
            self.cursor = self.connection.cursor()

            # Enable foreign keys
            self.cursor.execute("PRAGMA foreign_keys = ON")

            self.__create_tables()
            self.__initialize_owner()
            self._initialized = True

            logger.info(f"Database initialized at {db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}") from e

    @contextmanager
    def _execute_transaction(self, query: str, params: tuple = ()) -> Iterator[sqlite3.Cursor]:
        """Context manager for database transactions"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            yield cursor
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            logger.error(f"Database transaction error: {e}")
            raise DatabaseError(f"Transaction failed: {e}") from e

    def __create_tables(self) -> None:
        """Create tables if they don't exist"""
        table_definitions = {
            self.BOT_TABLE: [
                ("ID", "VARCHAR(25) NOT NULL PRIMARY KEY"),
                ("USERNAME", "VARCHAR(32) DEFAULT NULL UNIQUE"),
                ("NICK", "VARCHAR(32) DEFAULT '¿?'"),
                ("RANK", "VARCHAR(15) DEFAULT 'user'"),
                ("STATE", "VARCHAR(12) DEFAULT 'free'"),
                ("MEMBERSHIP", "VARCHAR(15) DEFAULT 'free user'"),
                ("EXPIRATION", "VARCHAR(20) DEFAULT NULL"),
                ("ANTISPAM", "INTEGER DEFAULT 60"),
                ("CREDITS", "INTEGER DEFAULT 0"),
                ("REGISTERED", "TEXT NOT NULL"),
                ("CHECKS", "INTEGER DEFAULT 0"),
            ],
            self.BOT_KEYS_TABLE: [
                ("BOT_KEY", "VARCHAR(30) NOT NULL PRIMARY KEY"),
                ("EXPIRATION", "TEXT NOT NULL"),
            ],
            self.BOT_GROUPS: [
                ("ID", "VARCHAR(30) NOT NULL PRIMARY KEY"),
                ("EXPIRATION", "TEXT NOT NULL"),
                ("PROVIDER", "VARCHAR(30) NOT NULL"),
            ],
        }

        try:
            for table_name, columns in table_definitions.items():
                columns_str = ", ".join([f"{col_name} {col_type}" for col_name, col_type in columns])
                create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
                self.cursor.execute(create_sql)
                logger.debug(f"Table {table_name} ready")

            self.connection.commit()
            logger.info("All tables created/verified successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to create tables: {e}")
            raise DatabaseError(f"Table creation failed: {e}") from e

    def __initialize_owner(self) -> None:
        """Initialize owner with admin privileges"""
        try:
            self.cursor.execute(
                f"SELECT * FROM {self.BOT_TABLE} WHERE ID = ?",
                (self.ID_OWNER,),
            )

            if not self.cursor.fetchone():
                now = datetime.datetime.now().isoformat()
                self.cursor.execute(
                    f"""INSERT INTO {self.BOT_TABLE} 
                       (ID, USERNAME, NICK, RANK, STATE, MEMBERSHIP, REGISTERED, CHECKS)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        self.ID_OWNER,
                        "Owner",
                        "👑 Owner",
                        "admin",
                        "active",
                        "vip",
                        now,
                        0,
                    ),
                )
                self.connection.commit()
                logger.info("Owner initialized")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize owner: {e}")
            raise DatabaseError(f"Owner initialization failed: {e}") from e

    def __enter__(self) -> "Database":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit"""
        if exc_type:
            logger.error(f"Context manager error: {exc_val}")
            self.connection.rollback()
        else:
            self.connection.commit()

    # User Management Methods

    def register_user(self, user_id: int, username: Optional[str] = None) -> bool:
        """Register or update a user"""
        try:
            now = datetime.datetime.now().isoformat()

            # Check if user exists
            self.cursor.execute(
                f"SELECT ID FROM {self.BOT_TABLE} WHERE ID = ?",
                (str(user_id),),
            )

            if self.cursor.fetchone():
                # Update existing user
                self.cursor.execute(
                    f"UPDATE {self.BOT_TABLE} SET USERNAME = ? WHERE ID = ?",
                    (username or "Unknown", str(user_id)),
                )
            else:
                # Insert new user
                self.cursor.execute(
                    f"""INSERT INTO {self.BOT_TABLE} 
                       (ID, USERNAME, REGISTERED)
                       VALUES (?, ?, ?)""",
                    (str(user_id), username or "Unknown", now),
                )

            self.connection.commit()
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to register user {user_id}: {e}")
            return False

    def is_ban(self, user_id: int) -> bool:
        """Check if user is banned"""
        try:
            self.cursor.execute(
                f"SELECT STATE FROM {self.BOT_TABLE} WHERE ID = ?",
                (str(user_id),),
            )
            result = self.cursor.fetchone()
            return result and result[0] == "banned" if result else False

        except sqlite3.Error as e:
            logger.error(f"Error checking ban status for {user_id}: {e}")
            return False

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        try:
            self.cursor.execute(
                f"SELECT RANK FROM {self.BOT_TABLE} WHERE ID = ?",
                (str(user_id),),
            )
            result = self.cursor.fetchone()
            return result and result[0] == "admin" if result else False

        except sqlite3.Error as e:
            logger.error(f"Error checking admin status for {user_id}: {e}")
            return False

    def is_premium(self, user_id: int) -> bool:
        """Check if user has premium access"""
        try:
            self.cursor.execute(
                f"SELECT MEMBERSHIP FROM {self.BOT_TABLE} WHERE ID = ?",
                (str(user_id),),
            )
            result = self.cursor.fetchone()

            if not result:
                return False

            membership = result[0]
            if membership not in ("premium", "vip"):
                return False

            # Check expiration
            self.cursor.execute(
                f"SELECT EXPIRATION FROM {self.BOT_TABLE} WHERE ID = ?",
                (str(user_id),),
            )
            expiration_row = self.cursor.fetchone()

            if expiration_row and expiration_row[0]:
                try:
                    expiration = datetime.datetime.fromisoformat(expiration_row[0])
                    return datetime.datetime.now() < expiration
                except ValueError:
                    logger.warning(f"Invalid expiration format for user {user_id}")
                    return True

            return True

        except sqlite3.Error as e:
            logger.error(f"Error checking premium status for {user_id}: {e}")
            return False

    def is_seller_or_admin(self, user_id: int) -> bool:
        """Check if user is seller or admin"""
        try:
            self.cursor.execute(
                f"SELECT RANK FROM {self.BOT_TABLE} WHERE ID = ?",
                (str(user_id),),
            )
            result = self.cursor.fetchone()
            return result and result[0] in ("admin", "seller") if result else False

        except sqlite3.Error as e:
            logger.error(f"Error checking seller/admin status for {user_id}: {e}")
            return False

    def user_has_credits(self, user_id: int) -> bool:
        """Check if user has available credits"""
        try:
            self.cursor.execute(
                f"SELECT CREDITS FROM {self.BOT_TABLE} WHERE ID = ?",
                (str(user_id),),
            )
            result = self.cursor.fetchone()
            return result and result[0] > 0 if result else False

        except sqlite3.Error as e:
            logger.error(f"Error checking credits for {user_id}: {e}")
            return False

    def get_info_user(self, user_id: int) -> Optional[Dict[str, Union[str, int]]]:
        """Get user information as dictionary"""
        try:
            self.cursor.execute(
                f"SELECT * FROM {self.BOT_TABLE} WHERE ID = ?",
                (str(user_id),),
            )
            row = self.cursor.fetchone()

            if not row:
                return None

            return dict(row)

        except sqlite3.Error as e:
            logger.error(f"Error retrieving user info for {user_id}: {e}")
            return None

    def remove_expireds_users(self) -> int:
        """Remove expired users and return count"""
        try:
            now = datetime.datetime.now().isoformat()

            self.cursor.execute(
                f"""DELETE FROM {self.BOT_TABLE} 
                   WHERE EXPIRATION IS NOT NULL AND EXPIRATION < ?""",
                (now,),
            )

            count = self.cursor.rowcount
            self.connection.commit()

            if count > 0:
                logger.info(f"Removed {count} expired users")

            return count

        except sqlite3.Error as e:
            logger.error(f"Error removing expired users: {e}")
            return 0

    def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        try:
            self.cursor.execute(
                f"UPDATE {self.BOT_TABLE} SET STATE = 'banned' WHERE ID = ?",
                (str(user_id),),
            )
            self.connection.commit()
            return self.cursor.rowcount > 0

        except sqlite3.Error as e:
            logger.error(f"Error banning user {user_id}: {e}")
            return False

    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        try:
            self.cursor.execute(
                f"UPDATE {self.BOT_TABLE} SET STATE = 'free' WHERE ID = ?",
                (str(user_id),),
            )
            self.connection.commit()
            return self.cursor.rowcount > 0

        except sqlite3.Error as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
            return False

    def add_credits(self, user_id: int, credits: int) -> bool:
        """Add credits to user"""
        try:
            self.cursor.execute(
                f"UPDATE {self.BOT_TABLE} SET CREDITS = CREDITS + ? WHERE ID = ?",
                (credits, str(user_id)),
            )
            self.connection.commit()
            return self.cursor.rowcount > 0

        except sqlite3.Error as e:
            logger.error(f"Error adding credits to user {user_id}: {e}")
            return False

    def get_user_count(self) -> int:
        """Get total user count"""
        try:
            self.cursor.execute(f"SELECT COUNT(*) FROM {self.BOT_TABLE}")
            result = self.cursor.fetchone()
            return result[0] if result else 0

        except sqlite3.Error as e:
            logger.error(f"Error getting user count: {e}")
            return 0

    def close(self) -> None:
        """Close database connection"""
        try:
            if self.connection:
                self.connection.close()
                logger.info("Database connection closed")
        except sqlite3.Error as e:
            logger.error(f"Error closing database: {e}")

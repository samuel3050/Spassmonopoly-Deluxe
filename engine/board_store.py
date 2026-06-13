import copy
import os
from contextlib import contextmanager

try:
    import mysql.connector
except ImportError:
    mysql = None
else:
    mysql = mysql.connector

from board_data import DEFAULT_FIELDS

from .game_engine import ensure_field_shape


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "spassmonopoly"),
}


def copy_fields(fields):
    return [dict(field) for field in fields]


class BoardStore:
    """Loads board configuration without depending on Flask or UI code."""

    def __init__(self):
        self._memory_fields = copy_fields(DEFAULT_FIELDS)
        self._use_mysql = os.getenv("DB_ENGINE", "sqlite").lower() == "mysql"
        self._db_status_checked = False
        self._db_available = False

    def _check_db(self):
        if self._db_status_checked:
            return self._db_available

        self._db_status_checked = True
        if not self._use_mysql or mysql is None:
            self._db_available = False
            return False

        try:
            connection = mysql.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) AS anzahl FROM spielfelder")
            result = cursor.fetchone() or {}
            self._db_available = int(result.get("anzahl", 0)) >= 40
        except Exception:
            self._db_available = False
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                connection.close()
            except Exception:
                pass

        return self._db_available

    @contextmanager
    def _db_cursor(self, dictionary=False):
        if not self._check_db():
            raise RuntimeError("Datenbank nicht verfügbar")

        connection = mysql.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=dictionary)
        try:
            yield cursor
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def load_fields(self):
        if self._check_db():
            try:
                with self._db_cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT * FROM spielfelder ORDER BY feld_id ASC")
                    return ensure_field_shape(cursor.fetchall())
            except Exception:
                self._db_available = False

        return ensure_field_shape(copy.deepcopy(self._memory_fields))

    def reset_owners(self):
        for field in self._memory_fields:
            field["besitzer"] = None

        if self._check_db():
            try:
                with self._db_cursor() as cursor:
                    cursor.execute("UPDATE spielfelder SET besitzer = NULL")
            except Exception:
                self._db_available = False


"""MySQL connection and read-only schema inspection helpers.

Connection settings are read from environment variables (optionally loaded from
the repository's local .env file). No credentials belong in source control.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # Allows environment variables without python-dotenv.
    load_dotenv = None

try:
    import mysql.connector
    from mysql.connector import MySQLConnection
except ImportError as exc:
    raise RuntimeError(
        "MySQL driver missing. Install dependencies with: "
        "python -m pip install -r backend/requirements.txt"
    ) from exc


def _load_local_env() -> None:
    if load_dotenv is not None:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def get_connection() -> MySQLConnection:
    """Open a MySQL connection using MYSQL_* environment variables."""
    _load_local_env()
    required = {
        "MYSQL_HOST": os.getenv("MYSQL_HOST"),
        "MYSQL_USER": os.getenv("MYSQL_USER"),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE"),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            f"Missing MySQL configuration: {names}. Set these in the process "
            "environment or in a local .env file; never commit real credentials."
        )

    try:
        port = int(os.getenv("MYSQL_PORT", "3306"))
    except ValueError as exc:
        raise RuntimeError("MYSQL_PORT must be a valid integer.") from exc

    return mysql.connector.connect(
        host=required["MYSQL_HOST"],
        port=port,
        user=required["MYSQL_USER"],
        password=required["MYSQL_PASSWORD"],
        database=required["MYSQL_DATABASE"],
        connection_timeout=int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10")),
    )


def inspect_schema(connection: MySQLConnection) -> list[dict[str, Any]]:
    """Return table and column metadata for the configured database only."""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT c.TABLE_NAME AS table_name,
                      c.COLUMN_NAME AS column_name,
                      c.COLUMN_TYPE AS column_type,
                      c.IS_NULLABLE AS is_nullable,
                      c.COLUMN_KEY AS column_key,
                      c.EXTRA AS extra
               FROM information_schema.COLUMNS AS c
               WHERE c.TABLE_SCHEMA = DATABASE()
               ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION"""
        )
        return cursor.fetchall()
    finally:
        cursor.close()

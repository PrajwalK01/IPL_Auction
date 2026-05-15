"""
db/connection.py — MySQL connection helper
"""

import mysql.connector
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def get_connection():
    """Return a new MySQL connection using settings in config.py."""
    try:
        return mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            autocommit=True,
            connection_timeout=10,
            charset="utf8mb4",
        )
    except mysql.connector.Error as e:
        raise ConnectionError(
            f"Cannot connect to MySQL at {config.DB_HOST}:{config.DB_PORT} "
            f"as '{config.DB_USER}'. Check your .env file.\nDetails: {e}"
        )

"""
config.py — Application configuration
Reads from environment variables or falls back to .env file values.
"""

import os

# Load .env file manually if python-dotenv is not installed
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

SECRET_KEY  = os.environ.get("SECRET_KEY",  "ipl_auction_super_secret_2026")

# DB Config
DB_HOST     = os.environ.get("DB_HOST", "localhost")
DB_PORT     = int(os.environ.get("DB_PORT", 3306))
DB_USER     = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME     = os.environ.get("DB_NAME", "ipl_auction_db")

# Firebase Config
FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET", "ipl-auction-fbe62.appspot.com")



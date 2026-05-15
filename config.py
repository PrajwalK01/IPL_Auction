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

# Firebase Config
FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET", "ipl-auction-fbe62.appspot.com")



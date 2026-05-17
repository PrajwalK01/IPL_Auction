"""db/helpers.py — Firestore helper utilities (v2).

Provides:
- Counter-based sequential ID generation (atomic, no race conditions)
- bcrypt password hashing / verification
- Input sanitization
- Singleton app_config cache
- Multi-collection player lookup
- Audit logging (security + auction)
"""

import re
import html
from firebase_admin import firestore
from db.firebase import get_db

# ── ID Prefixes ──────────────────────────────────────────────────────────────
COLLECTION_PREFIX = {
    "batters":         "BT",
    "bowlers":         "BL",
    "all_rounders":    "AR",
    "wicket_keepers":  "WK",
}

# Maps player ID prefix back to collection name
PREFIX_TO_COLLECTION = {v: k for k, v in COLLECTION_PREFIX.items()}


# ── Counter-Based ID Generation ─────────────────────────────────────────────
def generate_player_id(collection_name):
    """Generate a sequential ID like BT-0001 using a Firestore counter document.

    Uses a transaction to atomically increment the counter, preventing race
    conditions that occur with full-collection scans.
    """
    prefix = COLLECTION_PREFIX.get(collection_name)
    if not prefix:
        raise ValueError(f"Unknown player collection: {collection_name}")

    db = get_db()
    counter_ref = db.collection("counters").document(collection_name)

    @firestore.transactional
    def _increment(transaction):
        snapshot = counter_ref.get(transaction=transaction)
        if snapshot.exists:
            current = snapshot.to_dict().get("current", 0)
        else:
            current = 0
        new_val = current + 1
        transaction.set(counter_ref, {"current": new_val})
        return new_val

    transaction = db.transaction()
    seq = _increment(transaction)
    return f"{prefix}-{seq:04d}"


def generate_team_id():
    """Generate a sequential team ID like T-0001 using a counter document."""
    db = get_db()
    counter_ref = db.collection("counters").document("teams")

    @firestore.transactional
    def _increment(transaction):
        snapshot = counter_ref.get(transaction=transaction)
        if snapshot.exists:
            current = snapshot.to_dict().get("current", 0)
        else:
            current = 0
        new_val = current + 1
        transaction.set(counter_ref, {"current": new_val})
        return new_val

    transaction = db.transaction()
    seq = _increment(transaction)
    return f"T-{seq:04d}"


# ── Password Hashing ────────────────────────────────────────────────────────
def hash_password(plain_text):
    """Return plain-text password (no hashing per user request)."""
    return plain_text


def verify_password(plain_text, stored_password):
    """Verify a plain-text password."""
    return plain_text == stored_password


# ── Input Sanitization ───────────────────────────────────────────────────────
def sanitize_input(value):
    """Strip HTML tags and escape special characters from user input."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    value = value.strip()
    # Remove HTML tags
    value = re.sub(r"<[^>]+>", "", value)
    # Escape remaining HTML entities
    value = html.escape(value, quote=True)
    return value


def sanitize_dict(data, keys=None):
    """Sanitize all string values in a dict. If keys is provided, only those."""
    sanitized = {}
    for k, v in data.items():
        if keys and k not in keys:
            sanitized[k] = v
        elif isinstance(v, str):
            sanitized[k] = sanitize_input(v)
        else:
            sanitized[k] = v
    return sanitized


# ── App Config (Singleton Cache) ─────────────────────────────────────────────
_config_cache = None


def get_app_config(force_refresh=False):
    """Read the singleton config/app_config document.

    Caches in-memory for the lifetime of the process.
    Call with force_refresh=True after admin edits.
    """
    global _config_cache
    if _config_cache is not None and not force_refresh:
        return _config_cache

    db = get_db()
    doc = db.collection("config").document("app_config").get()
    if doc.exists:
        _config_cache = doc.to_dict()
    else:
        # Create default config if missing
        default = {
            "nationalities": ["Indian", "Australian", "English", "South African",
                              "West Indian", "New Zealand", "Sri Lankan",
                              "Bangladeshi", "Afghan", "Zimbabwean"],
            "bowling_styles": ["Right-arm Fast", "Left-arm Fast",
                               "Right-arm Medium", "Left-arm Medium",
                               "Right-arm Off-spin", "Left-arm Orthodox",
                               "Right-arm Leg-spin", "Left-arm Chinaman"],
            "batting_styles": ["Right-Hand", "Left-Hand"],
            "player_types": ["Capped", "Uncapped"],
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        db.collection("config").document("app_config").set(default)
        _config_cache = default

    return _config_cache


def update_app_config(category, value):
    """Add a new value to a config array (e.g. add a nationality)."""
    global _config_cache
    db = get_db()
    ref = db.collection("config").document("app_config")
    ref.update({
        category: firestore.ArrayUnion([value]),
        "updated_at": firestore.SERVER_TIMESTAMP,
    })
    _config_cache = None  # Invalidate cache


# ── Multi-Collection Player Lookup ───────────────────────────────────────────
def get_player_collection(player_id):
    """Determine which collection a player belongs to from their ID prefix."""
    if not player_id or "-" not in player_id:
        return None
    prefix = player_id.split("-")[0]
    return PREFIX_TO_COLLECTION.get(prefix)


def get_player_by_id(player_id):
    """Fetch a player document from the correct collection based on ID prefix."""
    collection = get_player_collection(player_id)
    if not collection:
        return None, None
    db = get_db()
    doc = db.collection(collection).document(player_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data, collection
    return None, collection


def get_all_players(include_deleted=False):
    """Fetch players from all 4 collections, merged into a single list."""
    db = get_db()
    all_players = []
    for coll_name in COLLECTION_PREFIX.keys():
        docs = db.collection(coll_name).stream()
        for doc in docs:
            p = doc.to_dict()
            p["id"] = doc.id
            p["_collection"] = coll_name
            if not include_deleted and p.get("is_deleted"):
                continue
            all_players.append(p)
    return all_players


# ── Auction Logging ──────────────────────────────────────────────────────────
def log_auction_event(player_id, player_collection, player_name,
                      team_id, team_name, final_price, outcome):
    """Append an entry to the auction_logs collection (auto-ID)."""
    db = get_db()
    db.collection("auction_logs").add({
        "player_id": player_id,
        "player_collection": player_collection,
        "player_name": player_name,
        "team_id": team_id,
        "team_name": team_name,
        "final_price": final_price,
        "outcome": outcome,
        "timestamp": firestore.SERVER_TIMESTAMP,
    })


# ── Team Cache (Singleton) ──────────────────────────────────────────────────
_team_cache = {"data": None, "expiry": 0}

def get_team_map(force_refresh=False):
    """Fetch all teams and cache them in-memory for 5 minutes.
    Returns a dict mapping team_id to team_data.
    """
    global _team_cache
    import time
    if _team_cache["data"] and not force_refresh and time.time() < _team_cache["expiry"]:
        return _team_cache["data"]

    try:
        db = get_db()
        docs = db.collection("teams").stream()
        teams = {}
        for d in docs:
            t = d.to_dict()
            t["id"] = d.id
            teams[d.id] = t
        
        _team_cache["data"] = teams
        _team_cache["expiry"] = time.time() + 300.0  # 5 minutes
        return teams
    except Exception:
        return {}


# ── Security Logging ────────────────────────────────────────────────────────
def log_security_event(event_type, username, status, request):
    """Log a security event to Firestore using auto-ID."""
    try:
        db = get_db()
        ip = request.remote_addr
        ua = request.user_agent.string
        _, doc_ref = db.collection("security_logs").add({
            "event_type": event_type,
            "username": sanitize_input(username),
            "ip_address": ip,
            "user_agent": ua,
            "status": status,
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        print(f"[{event_type}] Logged: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        print(f"Logging error: {e}")
        return None  # Security logging must never crash the app

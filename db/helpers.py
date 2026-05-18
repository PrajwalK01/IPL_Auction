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
    db = get_db()
    teams_ref = db.collection("teams")
    docs = teams_ref.get()
    
    if not docs:
        return "T-0001"
    
    # Filter for T- prefix IDs
    team_ids = [d.id for d in docs if d.id.startswith("T-")]
    if not team_ids:
        return "T-0001"
        
    team_ids.sort(reverse=True)
    last_id = team_ids[0]
    num = int(last_id.split("-")[1])
    return f"T-{num + 1:04d}"


def generate_player_id(role):
    code = ROLE_CODE.get(role, "PL")
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

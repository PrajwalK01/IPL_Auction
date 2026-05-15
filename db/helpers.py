from firebase_admin import firestore
from db.firebase import get_db

ROLE_CODE = {
    "Batsman":       "BAT",
    "Bowler":        "BWL",
    "All-Rounder":   "AR",
    "Wicket-Keeper Batter": "WK",
}


def generate_user_id():
    db = get_db()
    users_ref = db.collection("users")
    # Using 'UserName' as a proxy for ordering if ID is the document name
    docs = users_ref.get()
    
    if not docs:
        return "US-001"
    
    # Filter for US- prefix IDs
    user_ids = [d.id for d in docs if d.id.startswith("US-")]
    if not user_ids:
        return "US-001"
        
    user_ids.sort(reverse=True)
    last_id = user_ids[0]
    num = int(last_id.split("-")[1])
    return f"US-{num + 1:03d}"


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
    players_ref = db.collection("players")
    docs = players_ref.get()
    
    if not docs:
        return f"P-{code}-0001"
    
    p_ids = [d.id for d in docs if d.id.startswith(f"P-{code}-")]
    if not p_ids:
        return f"P-{code}-0001"
        
    p_ids.sort(reverse=True)
    last_id = p_ids[0]
    num = int(last_id.split("-")[-1])
    return f"P-{code}-{num + 1:04d}"


def generate_log_id():
    db = get_db()
    logs_ref = db.collection("security_logs")
    docs = logs_ref.get()
    
    if not docs:
        return "SL-0001"
    
    log_ids = [d.id for d in docs if d.id.startswith("SL-")]
    if not log_ids:
        return "SL-0001"
        
    log_ids.sort(reverse=True)
    last_id = log_ids[0]
    num = int(last_id.split("-")[1])
    return f"SL-{num + 1:04d}"


def log_security_event(event_type, username, status, request):
    """Logs a security event to Firestore with SL-0001 format ID."""
    try:
        db = get_db()
        log_id = generate_log_id()
        ip = request.remote_addr
        ua = request.user_agent.string
        
        db.collection("security_logs").document(log_id).set({
            "event_type": event_type,
            "username": username,
            "ip_address": ip,
            "user_agent": ua,
            "status": status,
            "created_at": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error logging security event: {e}")


# --- ID Generators for Dropdown Options ---

def generate_nationality_id():
    db = get_db()
    docs = db.collection("nationalities").get()
    if not docs: return "NT-0001"
    ids = [d.id for d in docs if d.id.startswith("NT-")]
    if not ids: return "NT-0001"
    ids.sort(reverse=True)
    num = int(ids[0].split("-")[1])
    return f"NT-{num + 1:04d}"

def generate_bowling_id():
    db = get_db()
    docs = db.collection("bowling_styles").get()
    if not docs: return "BS-0001"
    ids = [d.id for d in docs if d.id.startswith("BS-")]
    if not ids: return "BS-0001"
    ids.sort(reverse=True)
    num = int(ids[0].split("-")[1])
    return f"BS-{num + 1:04d}"

def generate_mentor_id():
    db = get_db()
    docs = db.collection("mentors").get()
    if not docs: return "M-001"
    ids = [d.id for d in docs if d.id.startswith("M-")]
    if not ids: return "M-001"
    ids.sort(reverse=True)
    num = int(ids[0].split("-")[1])
    return f"M-{num + 1:03d}"

def generate_player_type_id():
    db = get_db()
    docs = db.collection("player_types").get()
    if not docs: return "PT-0001"
    ids = [d.id for d in docs if d.id.startswith("PT-")]
    if not ids: return "PT-0001"
    ids.sort(reverse=True)
    num = int(ids[0].split("-")[1])
    return f"PT-{num + 1:04d}"

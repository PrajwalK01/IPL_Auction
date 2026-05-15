from firebase_admin import firestore
from db.firebase import get_db

def reseed_teams():
    try:
        db = get_db()
        
        # Delete old teams to avoid confusion
        old_docs = db.collection("teams").get()
        for d in old_docs:
            d.reference.delete()
        print("[CLEAN] Deleted old teams collection.")

        # Add Sample Team (RCB) with NEW SCHEMA
        tid = "T-0001"
        db.collection("teams").document(tid).set({
            "team_id": tid,
            "team_name": "Royal Challengers Bangalore",
            "team_short_name": "RCB",
            "owner_name": "United Spirits",
            "username": "rcb_owner",
            "password": "password123", # Plain text
            "player_purse": 80.0,
            "player_spent": 0.0,
            "mgmt_purse": 20.0,
            "mgmt_spent": 0.0,
            "total_purse": 100.0,
            "IsActive": True,
            "IsDeleted": False,
            "CreatedDate": firestore.SERVER_TIMESTAMP
        })
        print(f"[OK] Seeded Team {tid} (RCB) with new schema.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reseed_teams()

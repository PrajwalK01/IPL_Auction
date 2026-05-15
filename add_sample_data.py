"""
add_sample_data.py — Adds a sample user and a sample team to Firestore.
"""
from firebase_admin import firestore
from werkzeug.security import generate_password_hash
from db.firebase import get_db

def add_data():
    try:
        db = get_db()
        p_hash = generate_password_hash("admin123")
        
        # 1. Add an extra Staff User
        user_ref = db.collection("users").document("staff1")
        user_ref.set({
            "username": "staff1",
            "password_hash": p_hash,
            "role": "staff",
            "full_name": "Auction Operator",
            "email": "staff@ipl.com",
            "is_active": 1,
            "is_deleted": 0,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        print("[OK] Added User: staff1 / admin123")
        
        # 2. Add a Sample Team (Royal Challengers Bangalore)
        team_ref = db.collection("teams").document() # Auto-generated ID
        team_ref.set({
            "team_id": "T-001",
            "team_name": "Royal Challengers Bangalore",
            "team_short_name": "RCB",
            "owner_name": "United Spirits",
            "username": "rcb_owner",
            "password_hash": p_hash,
            "player_purse": 80.0,
            "player_spent": 0.0,
            "mgmt_purse": 20.0,
            "mgmt_spent": 0.0,
            "total_purse": 100.0,
            "is_active": 1,
            "is_deleted": 0,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        print("[OK] Added Team: RCB (Username: rcb_owner / Password: admin123)")
        
        print("\n✅ Sample data added to Firestore successfully!")
        
    except Exception as e:
        print(f"[FAIL] Error adding sample data: {e}")

if __name__ == "__main__":
    add_data()

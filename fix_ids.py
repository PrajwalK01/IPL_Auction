from firebase_admin import firestore
from db.firebase import get_db

def fix_all_ids():
    try:
        db = get_db()
        
        # 1. Clean up old collections to avoid ID format mixing
        for col in ["users", "teams", "security_logs"]:
            docs = db.collection(col).get()
            for d in docs:
                d.reference.delete()
            print(f"[CLEAN] Deleted all documents in '{col}'")

        # 2. Add Admin User (US-0001)
        db.collection("users").document("US-0001").set({
            "UserName": "admin",
            "Password": "admin123",
            "EmailId": "admin@ipl.com",
            "FullName": "System Administrator",
            "UserRole": "admin",
            "IsActive": True,
            "IsDelected": False,
            "CreatedDate": firestore.SERVER_TIMESTAMP
        })
        print("[OK] Created User US-0001 (admin)")

        # 3. Add Sample Team (T-0001)
        db.collection("teams").document("T-0001").set({
            "team_id": "T-0001",
            "team_name": "Royal Challengers Bangalore",
            "team_short_name": "RCB",
            "owner_name": "United Spirits",
            "username": "rcb_owner",
            "password_hash": "scrypt:32768:8:1$o333lkByKrM5Dawt$3447822a8bd76acbe90f062145226986d57cd5e8161d60d238b6954601e37847353cb72ed39e882e73318588285b9f18afacd1d8db074f67a1a40cc8d7877c89",
            "player_purse": 80.0,
            "player_spent": 0.0,
            "mgmt_purse": 20.0,
            "mgmt_spent": 0.0,
            "total_purse": 100.0,
            "is_active": 1,
            "is_deleted": 0,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        print("[OK] Created Team T-0001 (RCB)")

        print("\n✅ Database IDs Fixed and Seeded!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_all_ids()

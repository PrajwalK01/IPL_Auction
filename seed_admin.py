import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db.firebase import get_db

def seed():
    print("Seeding admin user...")
    db = get_db()
    
    # Seed Admin User
    admin_ref = db.collection("users").document("admin")
    if not admin_ref.get().exists:
        admin_ref.set({
            "username": "admin",
            "password": "adminpassword",
            "user_role": "admin",
            "is_active": True,
            "is_deleted": False,
        })
        print("Admin user created! Username: admin | Password: adminpassword")
    else:
        # Update password just to be sure
        admin_ref.update({"password": "adminpassword"})
        print("Admin user password reset to: adminpassword")
        
    # Seed Test Team
    team_docs = list(db.collection("teams").where("team_short_name", "==", "CSK").limit(1).stream())
    if not team_docs:
        team_ref = db.collection("teams").document()
        team_ref.set({
            "team_name": "Chennai Super Kings",
            "team_short_name": "CSK",
            "purse_remaining": 1000000,
            "squad_count": 0,
            "is_active": True,
            "is_deleted": False
        })
        
        cred_ref = team_ref.collection("credentials").document("login")
        cred_ref.set({
            "username": "csk",
            "password": "cskpassword"
        })
        print(f"Team created! Username: csk | Password: cskpassword")
    else:
        team_ref = team_docs[0].reference
        cred_ref = team_ref.collection("credentials").document("login")
        cred_ref.set({
            "username": "csk",
            "password": "cskpassword"
        })
        print("Team CSK password reset to: cskpassword")

if __name__ == "__main__":
    seed()

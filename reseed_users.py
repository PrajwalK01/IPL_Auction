from firebase_admin import firestore
from db.firebase import get_db
from db.helpers import generate_user_id

def reseed():
    try:
        db = get_db()
        
        # Delete old admin doc if it exists
        db.collection("users").document("admin").delete()
        
        # Create new Admin with US-001 ID and NEW SCHEMA
        uid = "US-001"
        admin_ref = db.collection("users").document(uid)
        admin_ref.set({
            "UserName": "admin",
            "Password": "admin123", # Plain text as requested
            "EmailId": "admin@ipl-auction.com",
            "FullName": "System Administrator",
            "UserRole": "admin",
            "IsActive": True,
            "IsDelected": False,
            "CreatedDate": firestore.SERVER_TIMESTAMP
        })
        
        print(f"[OK] Admin user seeded with ID: {uid}")
        print("     Username: admin | Password: admin123")
        
        # Create a sample Staff user
        sid = "US-002"
        staff_ref = db.collection("users").document(sid)
        staff_ref.set({
            "UserName": "staff1",
            "Password": "admin123",
            "EmailId": "staff1@ipl-auction.com",
            "FullName": "Staff Member 1",
            "UserRole": "staff",
            "IsActive": True,
            "IsDelected": False,
            "CreatedDate": firestore.SERVER_TIMESTAMP
        })
        print(f"[OK] Staff user seeded with ID: {sid}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reseed()

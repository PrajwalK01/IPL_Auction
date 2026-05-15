from firebase_admin import firestore
from werkzeug.security import generate_password_hash
from db.firebase import get_db

def reset_admin():
    try:
        db = get_db()
        p_hash = generate_password_hash("admin123")
        admin_ref = db.collection("users").document("admin")
        admin_ref.update({
            "password_hash": p_hash
        })
        print(f"[OK] Admin password reset to 'admin123'")
        print(f"Hash used: {p_hash}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_admin()

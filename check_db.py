from db.firebase import get_db

def check_users():
    try:
        db = get_db()
        users = db.collection("users").get()
        print(f"Total users found: {len(users)}")
        for u in users:
            d = u.to_dict()
            print(f"DocID: {u.id} | Username: {d.get('username')} | Active: {d.get('is_active')} | Deleted: {d.get('is_deleted')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_users()

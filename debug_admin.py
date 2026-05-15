from db.firebase import get_db

def debug_admin():
    db = get_db()
    doc = db.collection("users").document("admin").get()
    if doc.exists:
        data = doc.to_dict()
        uname = data.get('username')
        print(f"Username: '{uname}' | Length: {len(uname)}")
        for i, c in enumerate(uname):
            print(f"Char {i}: {c!r} (ord: {ord(c)})")
    else:
        print("Admin doc not found!")

if __name__ == "__main__":
    debug_admin()

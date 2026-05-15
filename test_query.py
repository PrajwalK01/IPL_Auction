from db.firebase import get_db

def test_query():
    try:
        db = get_db()
        username = "admin"
        users_ref = db.collection("users")
        user_docs = users_ref.where("username", "==", username).where("is_deleted", "==", 0).limit(1).get()
        print(f"Query for {username}: Found {len(user_docs)} docs")
        if user_docs:
            print(f"Data: {user_docs[0].to_dict()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_query()

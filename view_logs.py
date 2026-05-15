from db.firebase import get_db

def view_logs():
    try:
        db = get_db()
        logs = db.collection("security_logs").order_by("created_at", direction="DESCENDING").limit(10).get()
        print(f"Total logs found: {len(logs)}")
        for l in logs:
            d = l.to_dict()
            print(f"Time: {d.get('created_at')} | Event: {d.get('event_type')} | User: {d.get('username')} | Status: {d.get('status')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    view_logs()

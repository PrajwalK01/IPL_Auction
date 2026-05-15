from db.firebase import get_db

def seed_options():
    try:
        db = get_db()
        
        # 1. Nationalities
        nats = ["Indian", "Australian", "South African", "West Indian", "English", "New Zealander", "Sri Lankan", "Afghan"]
        for i, n in enumerate(nats):
            db.collection("nationalities").document(f"NT-{i+1:04d}").set({"name": n})
        print("[OK] Seeded Nationalities")

        # 2. Bowling Styles
        bowls = ["Right-arm Fast", "Right-arm Medium", "Right-arm Offbreak", "Right-arm Legbreak", "Left-arm Fast", "Left-arm Medium", "Left-arm Orthodox", "Left-arm Chinaman"]
        for i, b in enumerate(bowls):
            db.collection("bowling_styles").document(f"BS-{i+1:04d}").set({"name": b})
        print("[OK] Seeded Bowling Styles")

        # 3. Player Types
        types = ["Capped", "Uncapped"]
        for i, t in enumerate(types):
            db.collection("player_types").document(f"PT-{i+1:04d}").set({"name": t})
        print("[OK] Seeded Player Types")
        
    except Exception as e:
        print(f"Error seeding: {e}")

if __name__ == "__main__":
    seed_options()

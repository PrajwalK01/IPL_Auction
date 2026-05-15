from db.firebase import get_db

def migrate_roles():
    db = get_db()
    players = db.collection("players").where("role", "==", "Wicket-Keeper").get()
    
    count = 0
    for p in players:
        p.reference.update({"role": "Wicket-Keeper Batter"})
        count += 1
        
    print(f"[OK] Migrated {count} players from 'Wicket-Keeper' to 'Wicket-Keeper Batter'.")

if __name__ == "__main__":
    migrate_roles()

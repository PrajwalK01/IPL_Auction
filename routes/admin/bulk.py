"""routes/admin/bulk.py — Bulk player upload via Excel."""

import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from firebase_admin import firestore
from db.firebase import get_db
from db.helpers import generate_player_id, sanitize_input

bulk_bp = Blueprint("admin_bulk", __name__, url_prefix="/admin/bulk")

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_type") != "admin":
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

@bulk_bp.route("/upload", methods=["GET", "POST"])
@admin_required
def upload_players():
    if request.method == "POST":
        file = request.files.get("excel_file")
        if not file or file.filename == "":
            flash("No file selected.", "warning")
            return redirect(request.url)
        
        if not file.filename.endswith((".xlsx", ".xls")):
            flash("Please upload a valid Excel file (.xlsx or .xls).", "danger")
            return redirect(request.url)

        try:
            df = pd.read_excel(file)
            db = get_db()
            
            # Column mapping (Flexible matching)
            col_map = {
                "name": ["Name", "Player Name", "Player"],
                "type": ["Type", "Role", "Category"],
                "nationality": ["Nationality", "Country", "Nat"],
                "age": ["Age"],
                "batting_style": ["Batting Style", "Batting"],
                "bowling_style": ["Bowling Style", "Bowling"],
                "bowling_arm": ["Bowling Arm", "Arm"],
                "base_price": ["Base Price", "Price"],
                "matches": ["Matches", "Mts"],
                "economy": ["Economy", "Eco"],
                "wickets": ["Wickets", "Wkts"],
                "strike_rate": ["Strike Rate", "SR"],
                "stumpings": ["Stumpings", "St"],
                "catches": ["Catches", "Ct"],
                "status": ["Status", "Capped Status", "Capped"]
            }

            def get_col(df, key):
                for possible in col_map[key]:
                    if possible in df.columns: return possible
                return None

            stats = {"batters": 0, "bowlers": 0, "all_rounders": 0, "wicket_keepers": 0}
            
            for _, row in df.iterrows():
                p_type = str(row.get(get_col(df, "type"), "")).lower()
                
                collection = ""
                player_role = ""
                if "bat" in p_type:
                    collection = "batters"
                    player_role = "batter"
                elif "bowl" in p_type:
                    collection = "bowlers"
                    player_role = "bowler"
                elif "all" in p_type:
                    collection = "all_rounders"
                    player_role = "all_rounder"
                elif "wicket" in p_type or "wk" in p_type:
                    collection = "wicket_keepers"
                    player_role = "wicket_keeper"
                else:
                    continue # Skip unknown types

                player_id = generate_player_id(collection)
                
                data = {
                    "player_id": player_id,
                    "player_name": sanitize_input(str(row.get(get_col(df, "name"), "Unknown"))),
                    "player_type": player_role,
                    "nationality": sanitize_input(str(row.get(get_col(df, "nationality"), "Indian"))),
                    "age": int(row.get(get_col(df, "age"), 0)),
                    "batting_style": sanitize_input(str(row.get(get_col(df, "batting_style"), "Right-Hand"))),
                    "base_price": float(row.get(get_col(df, "base_price"), 0.20)),
                    "matches": int(row.get(get_col(df, "matches"), 0)),
                    "capped": str(row.get(get_col(df, "status"), "")).lower() == "capped",
                    "auction_status": "available",
                    "sold_to_team_id": None,
                    "sold_price": 0,
                    "is_deleted": False,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "photo": None
                }

                if collection == "batters":
                    data["strike_rate"] = float(row.get(get_col(df, "strike_rate"), 0))
                elif collection == "bowlers":
                    data["bowling_style"] = sanitize_input(str(row.get(get_col(df, "bowling_style"), "")))
                    data["bowling_arm"] = sanitize_input(str(row.get(get_col(df, "bowling_arm"), "")))
                    data["economy"] = float(row.get(get_col(df, "economy"), 0))
                    data["wickets"] = int(row.get(get_col(df, "wickets"), 0))
                elif collection == "all_rounders":
                    data["bowling_style"] = sanitize_input(str(row.get(get_col(df, "bowling_style"), "")))
                    data["strike_rate"] = float(row.get(get_col(df, "strike_rate"), 0))
                    data["economy"] = float(row.get(get_col(df, "economy"), 0))
                    data["wickets"] = int(row.get(get_col(df, "wickets"), 0))
                elif collection == "wicket_keepers":
                    data["strike_rate"] = float(row.get(get_col(df, "strike_rate"), 0))
                    data["stumpings"] = int(row.get(get_col(df, "stumpings"), 0))
                    data["catches"] = int(row.get(get_col(df, "catches"), 0))

                db.collection(collection).document(player_id).set(data)
                stats[collection] += 1

            from db.helpers import log_security_event
            log_security_event("BULK_PLAYER_IMPORT", session.get("username", "admin"), "success", request)
            
            flash(f"Success! Imported {sum(stats.values())} players. "
                  f"(BT: {stats['batters']}, BL: {stats['bowlers']}, AR: {stats['all_rounders']}, WK: {stats['wicket_keepers']})", "success")
            return redirect(url_for("dashboard.index"))

        except Exception as e:
            flash(f"Error processing file: {e}", "danger")
            return redirect(request.url)

    return render_template("admin/bulk_upload.html")
<<<<<<< HEAD


@bulk_bp.route("/seed-legends", methods=["POST"])
@admin_required
def seed_legends():
    try:
        db = get_db()
        
        legends = {
            "batters": [
                {"player_id": "BT-9001", "player_name": "Virat Kohli", "player_type": "batter", "nationality": "Indian", "age": 35, "batting_style": "Right-Hand", "base_price": 2.00, "matches": 237, "capped": True, "strike_rate": 130.02, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "BT-9002", "player_name": "Rohit Sharma", "player_type": "batter", "nationality": "Indian", "age": 36, "batting_style": "Right-Hand", "base_price": 2.00, "matches": 243, "capped": True, "strike_rate": 130.05, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "BT-9003", "player_name": "Suresh Raina", "player_type": "batter", "nationality": "Indian", "age": 37, "batting_style": "Left-Hand", "base_price": 1.50, "matches": 205, "capped": True, "strike_rate": 136.76, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "BT-9004", "player_name": "Chris Gayle", "player_type": "batter", "nationality": "West Indian", "age": 44, "batting_style": "Left-Hand", "base_price": 1.50, "matches": 142, "capped": True, "strike_rate": 148.96, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None}
            ],
            "bowlers": [
                {"player_id": "BL-9001", "player_name": "Lasith Malinga", "player_type": "bowler", "nationality": "Sri Lankan", "age": 40, "batting_style": "Right-Hand", "base_price": 2.00, "matches": 122, "capped": True, "bowling_style": "Right-arm Fast", "bowling_arm": "Right-Arm", "economy": 7.14, "wickets": 170, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "BL-9002", "player_name": "Jasprit Bumrah", "player_type": "bowler", "nationality": "Indian", "age": 30, "batting_style": "Right-Hand", "base_price": 2.00, "matches": 120, "capped": True, "bowling_style": "Right-arm Fast", "bowling_arm": "Right-Arm", "economy": 7.39, "wickets": 145, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "BL-9003", "player_name": "Rashid Khan", "player_type": "bowler", "nationality": "Afghan", "age": 25, "batting_style": "Right-Hand", "base_price": 1.50, "matches": 109, "capped": True, "bowling_style": "Right-arm Leg-spin", "bowling_arm": "Right-Arm", "economy": 6.67, "wickets": 139, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "BL-9004", "player_name": "Yuzvendra Chahal", "player_type": "bowler", "nationality": "Indian", "age": 33, "batting_style": "Right-Hand", "base_price": 1.50, "matches": 145, "capped": True, "bowling_style": "Right-arm Leg-spin", "bowling_arm": "Right-Arm", "economy": 7.66, "wickets": 187, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None}
            ],
            "all_rounders": [
                {"player_id": "AR-9001", "player_name": "Shane Watson", "player_type": "all_rounder", "nationality": "Australian", "age": 42, "batting_style": "Right-Hand", "base_price": 2.00, "matches": 145, "capped": True, "bowling_style": "Right-arm Medium", "strike_rate": 137.91, "economy": 7.87, "wickets": 92, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "AR-9002", "player_name": "Hardik Pandya", "player_type": "all_rounder", "nationality": "Indian", "age": 30, "batting_style": "Right-Hand", "base_price": 2.00, "matches": 115, "capped": True, "bowling_style": "Right-arm Medium", "strike_rate": 146.26, "economy": 8.35, "wickets": 53, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "AR-9003", "player_name": "Kieron Pollard", "player_type": "all_rounder", "nationality": "West Indian", "age": 36, "batting_style": "Right-Hand", "base_price": 1.50, "matches": 189, "capped": True, "bowling_style": "Right-arm Medium", "strike_rate": 149.87, "economy": 8.78, "wickets": 69, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "AR-9004", "player_name": "Ravindra Jadeja", "player_type": "all_rounder", "nationality": "Indian", "age": 35, "batting_style": "Left-Hand", "base_price": 2.00, "matches": 226, "capped": True, "bowling_style": "Left-arm Orthodox", "strike_rate": 128.56, "economy": 7.62, "wickets": 152, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None}
            ],
            "wicket_keepers": [
                {"player_id": "WK-9001", "player_name": "MS Dhoni", "player_type": "wicket_keeper", "nationality": "Indian", "age": 42, "batting_style": "Right-Hand", "base_price": 2.00, "matches": 250, "capped": True, "strike_rate": 135.92, "stumpings": 42, "catches": 142, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "WK-9002", "player_name": "AB de Villiers", "player_type": "wicket_keeper", "nationality": "South African", "age": 40, "batting_style": "Right-Hand", "base_price": 2.00, "matches": 184, "capped": True, "strike_rate": 151.68, "stumpings": 8, "catches": 118, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "WK-9003", "player_name": "Rishabh Pant", "player_type": "wicket_keeper", "nationality": "Indian", "age": 26, "batting_style": "Left-Hand", "base_price": 1.50, "matches": 98, "capped": True, "strike_rate": 147.97, "stumpings": 18, "catches": 75, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None},
                {"player_id": "WK-9004", "player_name": "Dinesh Karthik", "player_type": "wicket_keeper", "nationality": "Indian", "age": 38, "batting_style": "Right-Hand", "base_price": 1.00, "matches": 242, "capped": True, "strike_rate": 132.61, "stumpings": 36, "catches": 141, "auction_status": "available", "sold_to_team_id": None, "sold_price": 0, "is_deleted": False, "photo": None}
            ]
        }

        seeded_count = 0
        for collection_name, player_list in legends.items():
            for p in player_list:
                doc_ref = db.collection(collection_name).document(p["player_id"])
                if not doc_ref.get().exists:
                    doc_ref.set(p)
                    seeded_count += 1

        flash(f"Seeded {seeded_count} legendary IPL players successfully! 🌟", "success")
    except Exception as e:
        flash(f"Error seeding legends: {e}", "danger")
    return redirect(url_for("admin_bulk.upload_players"))
=======
>>>>>>> af413426eed48331f1d8932dfbb3f7c7a2bd8f48

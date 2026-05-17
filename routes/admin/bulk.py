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

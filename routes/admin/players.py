"""routes/admin/players.py — CRUD for players with dynamic dropdowns."""
import os
from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, current_app)
from werkzeug.utils import secure_filename
from db.firebase import get_db
from db.helpers import (generate_player_id, generate_nationality_id, 
                        generate_bowling_id, generate_player_type_id)
from firebase_admin import firestore

players_bp = Blueprint("admin_players", __name__, url_prefix="/admin/players")

ALLOWED = {"png", "jpg", "jpeg", "webp"}


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_type") != "admin":
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def save_photo(file):
    if not file or file.filename == "":
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        flash("Invalid file type. Use PNG, JPG or WEBP.", "warning")
        return None
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "players")
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(file.filename)
    file.save(os.path.join(upload_dir, filename))
    return filename


@players_bp.route("/")
@admin_required
def list_players():
    role_filter = request.args.get("role", "")
    try:
        db = get_db()
        # Fetch everything once to avoid index issues
        players_docs = db.collection("players").stream()
        teams_data = {d.id: d.to_dict() for d in db.collection("teams").stream()}
        
        players = []
        for doc in players_docs:
            p = doc.to_dict()
            if p.get("is_deleted") == 1: continue
            if role_filter and p.get("role") != role_filter: continue
            
            p['id'] = doc.id
            if p.get("sold_to_team_id"):
                team = teams_data.get(p["sold_to_team_id"])
                if team:
                    p["team_short_name"] = team.get("team_short_name")
            players.append(p)
            
        # Sort by player_id
        players.sort(key=lambda x: x.get("player_id", ""))
    except Exception as e:
        flash(f"Error loading players: {e}", "danger")
        players = []
    return render_template("admin/players.html", players=players, role_filter=role_filter)


@players_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_player():
    db = get_db()
    if request.method == "POST":
        f = request.form
        role = f.get("role", "")
        player_id = generate_player_id(role)
        photo_file = save_photo(request.files.get("photo"))
        try:
            db.collection("players").document(player_id).set({
                "player_id": player_id,
                "player_name": f["player_name"],
                "role": role,
                "nationality": f.get("nationality"),
                "age": int(f.get("age", 0)),
                "batting_style": f.get("batting_style"),
                "bowling_style": f.get("bowling_style"),
                "player_type": f.get("player_type"),
                "capped": 1 if f.get("player_type") == "Capped" else 0,
                "base_price": float(f.get("base_price", 0)),
                "matches": int(f.get("matches", 0)) if f.get("matches") else 0,
                "strike_rate": float(f.get("strike_rate", 0)) if f.get("strike_rate") else 0.0,
                "economy": float(f.get("economy", 0)) if f.get("economy") else 0.0,
                "photo": photo_file,
                "is_sold": 0,
                "sold_to_team_id": None,
                "is_active": 1,
                "is_deleted": 0,
                "created_at": firestore.SERVER_TIMESTAMP
            })
            flash(f"Player {player_id} added! ✅", "success")
            return redirect(url_for("admin_players.list_players"))
        except Exception as e:
            flash(f"Error adding player: {e}", "danger")

    # Fetch options for dropdowns
    nats = [d.to_dict()["name"] for d in db.collection("nationalities").stream()]
    bowls = [d.to_dict()["name"] for d in db.collection("bowling_styles").stream()]
    types = [d.to_dict()["name"] for d in db.collection("player_types").stream()]
    
    return render_template("admin/player_form.html", player=None, action="Add", 
                           nationalities=sorted(nats), bowling_styles=sorted(bowls), 
                           player_types=sorted(types))


@players_bp.route("/<string:pid>/edit", methods=["GET", "POST"])
@admin_required
def edit_player(pid):
    db = get_db()
    try:
        player_ref = db.collection("players").document(pid)
        player_doc = player_ref.get()
        if not player_doc.exists:
            flash("Player not found.", "warning")
            return redirect(url_for("admin_players.list_players"))
        
        player = player_doc.to_dict()
        player['id'] = pid

        if request.method == "POST":
            f = request.form
            photo = save_photo(request.files.get("photo")) or player.get("photo")
            
            data = {
                "player_name": f["player_name"],
                "role": f.get("role"),
                "nationality": f.get("nationality"),
                "age": int(f["age"]) if f.get("age") else 0,
                "batting_style": f.get("batting_style"),
                "bowling_style": f.get("bowling_style"),
                "player_type": f.get("player_type"),
                "capped": 1 if f.get("player_type") == "Capped" else 0,
                "base_price": float(f.get("base_price", 0)),
                "matches": int(f.get("matches", 0)) if f.get("matches") else 0,
                "strike_rate": float(f.get("strike_rate", 0)) if f.get("strike_rate") else 0.0,
                "economy": float(f.get("economy", 0)) if f.get("economy") else 0.0,
                "photo": photo,
                "is_active": int(f.get("is_active", 1))
            }
            player_ref.update(data)
            flash("Player updated successfully! ✅", "success")
            return redirect(url_for("admin_players.list_players"))
            
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("admin_players.list_players"))

    # Fetch options for dropdowns
    nats = [d.to_dict()["name"] for d in db.collection("nationalities").stream()]
    bowls = [d.to_dict()["name"] for d in db.collection("bowling_styles").stream()]
    types = [d.to_dict()["name"] for d in db.collection("player_types").stream()]

    return render_template("admin/player_form.html", player=player, action="Edit",
                           nationalities=sorted(nats), bowling_styles=sorted(bowls), 
                           player_types=sorted(types))


@players_bp.route("/add-option", methods=["POST"])
@admin_required
def add_option():
    """AJAX endpoint to add a new dropdown option."""
    data = request.json
    category = data.get("category")
    value = data.get("value")
    
    if not category or not value:
        return {"success": False, "error": "Missing data"}, 400
        
    try:
        db = get_db()
        if category == "nationality":
            oid = generate_nationality_id()
            db.collection("nationalities").document(oid).set({"name": value})
        elif category == "bowling":
            oid = generate_bowling_id()
            db.collection("bowling_styles").document(oid).set({"name": value})
        elif category == "type":
            oid = generate_player_type_id()
            db.collection("player_types").document(oid).set({"name": value})
        else:
            return {"success": False, "error": "Invalid category"}, 400
            
        return {"success": True, "id": oid, "value": value}
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


@players_bp.route("/import", methods=["POST"])
@admin_required
def import_players():
    import pandas as pd
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Please select a CSV or Excel file.", "warning")
        return redirect(url_for("admin_players.list_players"))
        
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
            
        db = get_db()
        count = 0
        
        # Required columns mapping (Case insensitive)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        
        for _, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            if not name: continue
            
            role = str(row.get("role", "Batsman")).strip()
            # Generate ID based on role
            pid = generate_player_id(role)
            
            # Cap base price at 2.0 Cr as requested
            base_price = float(row.get("base_price", 0.20))
            if base_price > 2.0:
                base_price = 2.0
                
            data = {
                "player_id": pid,
                "player_name": name,
                "role": role,
                "nationality": str(row.get("nationality", "Indian")),
                "age": int(row.get("age", 25)),
                "batting_style": str(row.get("batting_style", "Right-Hand")),
                "bowling_style": str(row.get("bowling_style", "N/A")),
                "player_type": str(row.get("player_type", "Uncapped")),
                "capped": 1 if str(row.get("player_type", "")).lower() == "capped" else 0,
                "base_price": base_price,
                "matches": int(row.get("matches", 0)),
                "strike_rate": float(row.get("strike_rate", 0)),
                "economy": float(row.get("economy", 0)),
                "photo": None,
                "is_sold": 0,
                "sold_to_team_id": None,
                "is_active": 1,
                "is_deleted": 0,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            
            db.collection("players").document(pid).set(data)
            count += 1
            
        flash(f"Successfully imported {count} players! 🚀", "success")
    except Exception as e:
        flash(f"Import failed: {str(e)}", "danger")
        
    return redirect(url_for("admin_players.list_players"))


@players_bp.route("/<string:pid>/delete", methods=["POST"])
@admin_required
def delete_player(pid):
    try:
        db = get_db()
        db.collection("players").document(pid).update({
            "is_deleted": 1,
            "is_active": 0
        })
        flash("Player removed successfully.", "info")
    except Exception as e:
        flash(f"Error deleting player: {e}", "danger")
    return redirect(url_for("admin_players.list_players"))

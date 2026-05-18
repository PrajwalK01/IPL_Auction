"""routes/admin/all_rounders.py — CRUD for All-Rounder players."""

from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash)
from firebase_admin import firestore
from db.firebase import get_db, upload_file_to_firebase
from db.helpers import (generate_player_id, get_app_config, update_app_config,
                        sanitize_input, get_team_map)

all_rounders_bp = Blueprint("admin_all_rounders", __name__,
                            url_prefix="/admin/all-rounders")

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}
COLLECTION = "all_rounders"


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_type") != "admin":
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def _save_photo(file):
    if not file or file.filename == "":
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        flash("Invalid file type. Use PNG, JPG or WEBP.", "warning")
        return None
    try:
        return upload_file_to_firebase(file, "players/all_rounders")
    except Exception as e:
        flash(f"Upload failed: {e}", "danger")
        return None


@all_rounders_bp.route("/")
@admin_required
def list_all_rounders():
    try:
        db = get_db()
        # Optimization: Limit to 50 to save reads, use cache for teams
        docs = db.collection(COLLECTION).limit(50).stream()
        teams_data = get_team_map()

        players = []
        for doc in docs:
            p = doc.to_dict()
            if p.get("is_deleted"):
                continue
            p["id"] = doc.id
            if p.get("sold_to_team_id"):
                team = teams_data.get(p["sold_to_team_id"])
                if team:
                    p["team_short_name"] = team.get("team_short_name")
            players.append(p)

        players.sort(key=lambda x: x.get("player_id", ""))
    except Exception as e:
        flash(f"Error loading all-rounders: {e}", "danger")
        players = []
    return render_template("admin/players.html", players=players,
                           player_type="All-Rounders", collection=COLLECTION)


@all_rounders_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_all_rounder():
    db = get_db()
    if request.method == "POST":
        f = request.form
        player_id = generate_player_id(COLLECTION)
        photo_url = _save_photo(request.files.get("photo"))
        try:
            db.collection(COLLECTION).document(player_id).set({
                "player_id": player_id,
                "player_name": sanitize_input(f["player_name"]),
                "player_type": "all_rounder",
                "nationality": sanitize_input(f.get("nationality", "")),
                "age": int(f.get("age", 0)) if f.get("age") else 0,
                "batting_style": sanitize_input(f.get("batting_style", "")),
                "bowling_style": sanitize_input(f.get("bowling_style", "")),
                "base_price": float(f.get("base_price", 0.20)),
                "matches": int(f.get("matches", 0)) if f.get("matches") else 0,
                "strike_rate": float(f.get("strike_rate", 0)) if f.get("strike_rate") else 0.0,
                "economy": float(f.get("economy", 0)) if f.get("economy") else 0.0,
                "wickets": int(f.get("wickets", 0)) if f.get("wickets") else 0,
                "capped": f.get("capped_status") == "Capped",
                "photo": photo_url,
                "auction_status": "available",
                "sold_to_team_id": None,
                "sold_price": 0,
                "is_deleted": False,
                "created_at": firestore.SERVER_TIMESTAMP,
            })
            flash(f"All-Rounder {player_id} added! ✅", "success")
            return redirect(url_for("admin_all_rounders.list_all_rounders"))
        except Exception as e:
            flash(f"Error adding all-rounder: {e}", "danger")

    cfg = get_app_config()
    return render_template("admin/all_rounder_form.html", player=None, action="Add",
                           nationalities=sorted(cfg.get("nationalities", [])),
                           bowling_styles=sorted(cfg.get("bowling_styles", [])),
                           batting_styles=cfg.get("batting_styles", []),
                           player_types=cfg.get("player_types", []))


@all_rounders_bp.route("/<string:pid>/edit", methods=["GET", "POST"])
@admin_required
def edit_all_rounder(pid):
    db = get_db()
    try:
        player_ref = db.collection(COLLECTION).document(pid)
        player_doc = player_ref.get()
        if not player_doc.exists:
            flash("All-Rounder not found.", "warning")
            return redirect(url_for("admin_all_rounders.list_all_rounders"))

        player = player_doc.to_dict()
        player["id"] = pid

        if request.method == "POST":
            f = request.form
            photo = _save_photo(request.files.get("photo")) or player.get("photo")
            data = {
                "player_name": sanitize_input(f["player_name"]),
                "nationality": sanitize_input(f.get("nationality", "")),
                "age": int(f["age"]) if f.get("age") else 0,
                "batting_style": sanitize_input(f.get("batting_style", "")),
                "bowling_style": sanitize_input(f.get("bowling_style", "")),
                "base_price": float(f.get("base_price", 0.20)),
                "matches": int(f.get("matches", 0)) if f.get("matches") else 0,
                "strike_rate": float(f.get("strike_rate", 0)) if f.get("strike_rate") else 0.0,
                "economy": float(f.get("economy", 0)) if f.get("economy") else 0.0,
                "wickets": int(f.get("wickets", 0)) if f.get("wickets") else 0,
                "capped": f.get("capped_status") == "Capped",
                "photo": photo,
            }
            player_ref.update(data)
            flash("All-Rounder updated successfully! ✅", "success")
            return redirect(url_for("admin_all_rounders.list_all_rounders"))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("admin_all_rounders.list_all_rounders"))

    cfg = get_app_config()
    return render_template("admin/all_rounder_form.html", player=player, action="Edit",
                           nationalities=sorted(cfg.get("nationalities", [])),
                           bowling_styles=sorted(cfg.get("bowling_styles", [])),
                           batting_styles=cfg.get("batting_styles", []),
                           player_types=cfg.get("player_types", []))


@all_rounders_bp.route("/<string:pid>/delete", methods=["POST"])
@admin_required
def delete_all_rounder(pid):
    try:
        db = get_db()
        db.collection(COLLECTION).document(pid).update({
            "is_deleted": True,
            "auction_status": "unavailable",
        })
        flash("All-Rounder removed successfully.", "info")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("admin_all_rounders.list_all_rounders"))


@all_rounders_bp.route("/add-option", methods=["POST"])
@admin_required
def add_option():
    data = request.json
    category = data.get("category")
    value = sanitize_input(data.get("value"))
    if not category or not value:
        return {"success": False, "error": "Missing data"}, 400

    category_map = {
        "nationality": "nationalities",
        "bowling": "bowling_styles",
        "type": "player_types",
    }
    config_key = category_map.get(category)
    if not config_key:
        return {"success": False, "error": "Invalid category"}, 400

    try:
        update_app_config(config_key, value)
        return {"success": True, "value": value}
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

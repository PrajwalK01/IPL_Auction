"""routes/admin/teams.py — CRUD for IPL teams with new schema."""
import os
from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, current_app)
from werkzeug.utils import secure_filename
from firebase_admin import firestore
from db.firebase import get_db
from db.helpers import generate_team_id

teams_bp = Blueprint("admin_teams", __name__, url_prefix="/admin/teams")

ALLOWED = {"png", "jpg", "jpeg", "gif", "webp", "svg"}


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_type") != "admin":
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def save_logo(file, username):
    if not file or file.filename == "":
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        flash("Invalid file type. Use PNG, JPG, GIF, WEBP or SVG.", "warning")
        return None
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "logos")
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(f"{username}_{file.filename}")
    file.save(os.path.join(upload_dir, filename))
    return filename


@teams_bp.route("/")
@admin_required
def list_teams():
    try:
        db = get_db()
        # Fetch all players and teams for in-memory processing
        all_players = [d.to_dict() for d in db.collection("players").stream()]
        teams_docs = db.collection("teams").stream()
        
        teams = []
        for doc in teams_docs:
            t = doc.to_dict()
            # USE NEW SCHEMA IsDeleted
            if t.get("IsDeleted") == True or t.get("is_deleted") == 1: continue
            
            t['id'] = doc.id
            # Aggregate squad size from already fetched players
            squad = [p for p in all_players if p.get("sold_to_team_id") == t.get("team_id") and p.get("is_deleted") == 0]
            t['squad_size'] = len(squad)
            t['player_remaining'] = float(t.get("player_purse", 80.0)) - float(t.get("player_spent", 0))
            t['mgmt_remaining'] = float(t.get("mgmt_purse", 20.0)) - float(t.get("mgmt_spent", 0))
            teams.append(t)
            
        # Sort by team_id ASC in Python
        teams.sort(key=lambda x: x.get("team_id", ""))
    except Exception as e:
        flash(f"Error loading teams: {e}", "danger")
        teams = []
    return render_template("admin/teams.html", teams=teams)


@teams_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_team():
    if request.method == "POST":
        f = request.form
        username = f["username"]
        logo_file = save_logo(request.files.get("team_logo"), username)
        team_id = generate_team_id()
        
        p_purse = float(f.get("player_purse", 80.0))
        m_purse = float(f.get("mgmt_purse", 20.0))
        
        try:
            db = get_db()
            db.collection("teams").document(team_id).set({
                "team_id": team_id,
                "team_name": f["team_name"],
                "team_short_name": f["team_short_name"].upper(),
                "owner_name": f.get("owner_name"),
                "team_logo": logo_file,
                "player_purse": p_purse,
                "player_spent": 0,
                "mgmt_purse": m_purse,
                "mgmt_spent": 0,
                "total_purse": p_purse + m_purse,
                "username": username,
                "password": f["password"], # PLAIN TEXT
                "IsActive": True,
                "IsDeleted": False,
                "CreatedDate": firestore.SERVER_TIMESTAMP
            })

            flash(f"Team {team_id} added successfully! ✅", "success")
            return redirect(url_for("admin_teams.list_teams"))
        except Exception as e:
            flash(f"Error adding team: {e}", "danger")
    return render_template("admin/team_form.html", team=None, action="Add")


@teams_bp.route("/<string:tid>/edit", methods=["GET", "POST"])
@admin_required
def edit_team(tid):
    try:
        db = get_db()
        team_ref = db.collection("teams").document(tid)
        team_doc = team_ref.get()
        if not team_doc.exists:
            flash("Team not found.", "warning")
            return redirect(url_for("admin_teams.list_teams"))
        
        team = team_doc.to_dict()
        team['id'] = tid

        if request.method == "POST":
            f = request.form
            logo_file = save_logo(request.files.get("team_logo"), f["username"]) or team.get("team_logo")
            
            p_purse = float(f.get("player_purse", 80.0))
            m_purse = float(f.get("mgmt_purse", 20.0))
            
            data = {
                "team_name": f["team_name"],
                "team_short_name": f["team_short_name"].upper(),
                "owner_name": f.get("owner_name"),
                "team_logo": logo_file,
                "player_purse": p_purse,
                "mgmt_purse": m_purse,
                "total_purse": p_purse + m_purse,
                "username": f["username"],
                "IsActive": f.get("IsActive") == "on" or f.get("IsActive") == "1"
            }
            
            if f.get("password"):
                data["password"] = f["password"]
            
            team_ref.update(data)
            flash("Team updated successfully! ✅", "success")
            return redirect(url_for("admin_teams.list_teams"))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("admin_teams.list_teams"))

    return render_template("admin/team_form.html", team=team, action="Edit")


@teams_bp.route("/<string:tid>/delete", methods=["POST"])
@admin_required
def delete_team(tid):
    try:
        db = get_db()
        db.collection("teams").document(tid).update({
            "IsDeleted": True,
            "IsActive": False
        })
        flash("Team removed successfully.", "info")
    except Exception as e:
        flash(f"Error deleting team: {e}", "danger")
    return redirect(url_for("admin_teams.list_teams"))


@teams_bp.route("/credentials")
@admin_required
def team_credentials():
    try:
        db = get_db()
        teams_docs = db.collection("teams").stream()
        teams = []
        for doc in teams_docs:
            t = doc.to_dict()
            if t.get("IsDeleted") == True: continue
            t['id'] = doc.id
            teams.append(t)
        # Sort by team_id ASC
        teams.sort(key=lambda x: x.get("team_id", ""))
    except Exception as e:
        flash(f"Error loading credentials: {e}", "danger")
        teams = []
    return render_template("admin/team_credentials.html", teams=teams)

"""routes/admin/teams.py — CRUD for IPL teams with credentials subcollection."""

from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash)
from firebase_admin import firestore
from db.firebase import get_db, upload_file_to_firebase
from db.helpers import (generate_team_id, hash_password, sanitize_input,
                        log_security_event)

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


def _save_logo(file):
    if not file or file.filename == "":
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        flash("Invalid file type.", "warning")
        return None
    try:
        return upload_file_to_firebase(file, "logos")
    except Exception as e:
        flash(f"Upload failed: {e}", "danger")
        return None


@teams_bp.route("/")
@admin_required
def list_teams():
    try:
        db = get_db()
        teams_docs = db.collection("teams").stream()

        teams = []
        for doc in teams_docs:
            t = doc.to_dict()
            if t.get("is_deleted"):
                continue
            t["id"] = doc.id
            t["player_remaining"] = (float(t.get("player_purse", 80.0))
                                     - float(t.get("player_spent", 0)))
            t["mgmt_remaining"] = (float(t.get("mgmt_purse", 20.0))
                                   - float(t.get("mgmt_spent", 0)))
            teams.append(t)

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
        username = sanitize_input(f["username"])
        password = f["password"]
        logo_file = _save_logo(request.files.get("team_logo"))
        team_id = generate_team_id()

        p_purse = float(f.get("player_purse", 80.0))
        m_purse = float(f.get("mgmt_purse", 20.0))

        try:
            db = get_db()

            # Create team document with credentials stored directly
            db.collection("teams").document(team_id).set({
                "team_id": team_id,
                "team_name": sanitize_input(f["team_name"]),
                "team_short_name": sanitize_input(f["team_short_name"]).upper(),
                "owner_name": sanitize_input(f.get("owner_name", "")),
                "home_ground": sanitize_input(f.get("home_ground", "")),
                "team_logo": logo_file,
                "player_purse": p_purse,
                "player_spent": 0,
                "mgmt_purse": m_purse,
                "mgmt_spent": 0,
                "total_purse": p_purse + m_purse,
                "squad_count": 0,
                "username": username,
                "password": password,
                "is_active": True,
                "is_deleted": False,
                "created_at": firestore.SERVER_TIMESTAMP,
            })

            log_security_event("TEAM_CREATED", f"Team {team_id}", "success", request)

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
        team["id"] = tid

        if request.method == "POST":
            f = request.form
            logo_file = (_save_logo(request.files.get("team_logo"))
                         or team.get("team_logo"))

            p_purse = float(f.get("player_purse", 80.0))
            m_purse = float(f.get("mgmt_purse", 20.0))

            data = {
                "team_name": sanitize_input(f["team_name"]),
                "team_short_name": sanitize_input(f["team_short_name"]).upper(),
                "owner_name": sanitize_input(f.get("owner_name", "")),
                "home_ground": sanitize_input(f.get("home_ground", "")),
                "team_logo": logo_file,
                "player_purse": p_purse,
                "mgmt_purse": m_purse,
                "total_purse": p_purse + m_purse,
                "is_active": f.get("is_active") in ("on", "1", "true"),
            }
            
            # Update password if provided
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
            "is_deleted": True,
            "is_active": False,
        })
        flash("Team removed successfully.", "info")
    except Exception as e:
        flash(f"Error: {e}", "danger")
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
            if t.get("is_deleted"):
                continue
            t["id"] = doc.id

            t["username"] = t.get("username", "—")

            teams.append(t)
        teams.sort(key=lambda x: x.get("team_id", ""))
    except Exception as e:
        flash(f"Error loading credentials: {e}", "danger")
        teams = []
    return render_template("admin/team_credentials.html", teams=teams)


@teams_bp.route("/<string:tid>/reset-password", methods=["POST"])
@admin_required
def reset_password(tid):
    """Reset a team's password (admin only)."""
    new_password = request.form.get("new_password", "").strip()
    if not new_password or len(new_password) < 4:
        flash("Password must be at least 4 characters.", "warning")
        return redirect(url_for("admin_teams.team_credentials"))

    try:
        db = get_db()
        db.collection("teams").document(tid).update({
            "password": new_password,
        })
        flash("Password reset successfully! ✅", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("admin_teams.team_credentials"))
<<<<<<< HEAD


IPL_FRANCHISES = [
    {"id": "CSK", "name": "Chennai Super Kings", "short_name": "CSK", "logo": "/static/img/ipl_logos/CSK.svg", "color": "#FFFF00"},
    {"id": "RCB", "name": "Royal Challengers Bengaluru", "short_name": "RCB", "logo": "/static/img/ipl_logos/RCB.svg", "color": "#EC1C24"},
    {"id": "MI", "name": "Mumbai Indians", "short_name": "MI", "logo": "/static/img/ipl_logos/MI.svg", "color": "#004BA0"},
    {"id": "KKR", "name": "Kolkata Knight Riders", "short_name": "KKR", "logo": "/static/img/ipl_logos/KKR.svg", "color": "#3A225D"},
    {"id": "RR", "name": "Rajasthan Royals", "short_name": "RR", "logo": "/static/img/ipl_logos/RR.svg", "color": "#EA1B85"},
    {"id": "SRH", "name": "Sunrisers Hyderabad", "short_name": "SRH", "logo": "/static/img/ipl_logos/SRH.svg", "color": "#FF822E"},
    {"id": "LSG", "name": "Lucknow Super Giants", "short_name": "LSG", "logo": "/static/img/ipl_logos/LSG.svg", "color": "#0057E7"},
    {"id": "GT", "name": "Gujarat Titans", "short_name": "GT", "logo": "/static/img/ipl_logos/GT.svg", "color": "#0B2240"},
    {"id": "DC", "name": "Delhi Capitals", "short_name": "DC", "logo": "/static/img/ipl_logos/DC.svg", "color": "#005CA8"},
    {"id": "PBKS", "name": "Punjab Kings", "short_name": "PBKS", "logo": "/static/img/ipl_logos/PBKS.svg", "color": "#D71920"}
]



@teams_bp.route("/assign", methods=["GET", "POST"])
@admin_required
def assign_ipl():
    db = get_db()
    if request.method == "POST":
        try:
            assignments = request.form.to_dict()
            for tid, ipl_id in assignments.items():
                if not tid.startswith("TE-"):
                    continue
                if not ipl_id:
                    # Unassign / reset
                    t_doc = db.collection("teams").document(tid).get().to_dict()
                    orig = t_doc.get("original_name") or "Team"
                    db.collection("teams").document(tid).update({
                        "team_name": orig,
                        "team_short_name": "TEAM",
                        "team_logo": None,
                        "ipl_franchise_id": None
                    })
                    continue

                franchise = next((f for f in IPL_FRANCHISES if f["id"] == ipl_id), None)
                if franchise:
                    team_ref = db.collection("teams").document(tid)
                    t_data = team_ref.get().to_dict()
                    original_name = t_data.get("original_name") or t_data.get("team_name")
                    
                    update_data = {
                        "original_name": original_name,
                        "team_name": franchise["name"],
                        "team_short_name": franchise["short_name"],
                        "team_color": franchise["color"],
                        "ipl_franchise_id": franchise["id"]
                    }
                    
                    # Manual logo file upload check
                    logo_file = request.files.get(f"logo_{tid}")
                    if logo_file and logo_file.filename != "":
                        logo_url = _save_logo(logo_file)
                        if logo_url:
                            update_data["team_logo"] = logo_url

                    team_ref.update(update_data)
            flash("IPL franchises assigned successfully! 🏏", "success")
            return redirect(url_for("admin_teams.list_teams"))
        except Exception as e:
            flash(f"Error assigning franchises: {e}", "danger")

    try:
        teams_docs = db.collection("teams").stream()
        teams = []
        for doc in teams_docs:
            t = doc.to_dict()
            if t.get("is_deleted"):
                continue
            t["id"] = doc.id
            teams.append(t)
        teams.sort(key=lambda x: x.get("team_id", ""))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        teams = []

    return render_template("admin/assign_ipl.html", teams=teams, franchises=IPL_FRANCHISES)


@teams_bp.route("/simulation", methods=["GET"])
@admin_required
def simulation():
    db = get_db()
    try:
        teams_docs = db.collection("teams").stream()
        teams = []
        for doc in teams_docs:
            t = doc.to_dict()
            if t.get("is_deleted"):
                continue
            t["id"] = doc.id
            teams.append(t)
        teams.sort(key=lambda x: x.get("team_id", ""))

        pred_doc = db.collection("auction_state").document("standing_prediction").get()
        predictions = pred_doc.to_dict().get("standings") if pred_doc.exists else None

    except Exception as e:
        flash(f"Error loading simulation: {e}", "danger")
        teams = []
        predictions = None

    return render_template("admin/simulation.html", teams=teams, predictions=predictions)


@teams_bp.route("/simulation/run", methods=["POST"])
@admin_required
def run_simulation():
    from db.ai_predictor import run_ai_simulation
    try:
        res = run_ai_simulation()
        if isinstance(res, dict) and "error" in res:
            flash(res["error"], "warning")
        else:
            flash("AI Standings Prediction simulated successfully! 🏆", "success")
    except Exception as e:
        flash(f"Simulation failed: {e}", "danger")
    return redirect(url_for("admin_teams.simulation"))
=======
>>>>>>> af413426eed48331f1d8932dfbb3f7c7a2bd8f48

"""routes/dashboard.py — Admin dashboard with live stats."""
from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, flash
from db.firebase import get_db

dashboard_bp = Blueprint("dashboard", __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_type") != "admin":
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@dashboard_bp.route("/dashboard")
@admin_required
def index():
    try:
        db = get_db()

        # Fetch all players and teams once to avoid complex indexed queries
        all_players = [d.to_dict() for d in db.collection("players").stream()]
        all_teams   = [d.to_dict() for d in db.collection("teams").stream()]

        # Filter in Python (Avoids Firebase Index errors) - Resilient to key casing
        active_players = [p for p in all_players if (p.get("is_deleted") == 0 or p.get("IsDeleted") == False) and (p.get("is_active") == 1 or p.get("IsActive") == True)]
        active_teams   = [t for t in all_teams if (t.get("IsDeleted") == False or t.get("is_deleted") == 0) and (t.get("IsActive") == True or t.get("is_active") == 1)]

        total_players = len(active_players)
        total_teams   = len(active_teams)

        # Aggregate Purses
        total_player_purse = 0
        total_mgmt_purse = 0
        total_overall_purse = 0
        teams_list = []
        
        for t in active_teams:
            p_purse = float(t.get("player_purse", 0))
            m_purse = float(t.get("mgmt_purse", 0))
            total_player_purse += p_purse
            total_mgmt_purse += m_purse
            total_overall_purse += (p_purse + m_purse)
            
            # Squad size (Filter from our already fetched list)
            squad = [p for p in all_players if p.get("sold_to_team_id") == t.get("team_id") and p.get("is_deleted") == 0]
            t['squad_size'] = len(squad)
            t['player_remaining'] = p_purse - float(t.get("player_spent", 0))
            t['mgmt_remaining'] = m_purse - float(t.get("mgmt_spent", 0))
            teams_list.append(t)

        # Total Bids
        all_bids = [d.to_dict() for d in db.collection("bids").stream()]
        total_bids = len([b for b in all_bids if b.get("is_deleted") == 0])

        # Sold Players count
        sold_players = len([p for p in active_players if p.get("is_sold") == 1])

        # Recent Players (Sort in Python)
        recent_players = sorted(
            [p for p in all_players if p.get("is_deleted") == 0],
            key=lambda x: x.get("created_at") or 0,
            reverse=True
        )[:8]

    except Exception as e:
        flash(f"Dashboard error: {e}", "danger")
        teams_list = []
        recent_players = []
        total_players = total_teams = total_bids = sold_players = 0
        total_player_purse = total_mgmt_purse = total_overall_purse = 0

    return render_template("dashboard.html",
        username      = session.get("username"),
        role          = session.get("role"),
        total_players = total_players,
        total_teams   = total_teams,
        total_player_purse = total_player_purse,
        total_mgmt_purse   = total_mgmt_purse,
        total_overall_purse = total_overall_purse,
        total_bids    = total_bids,
        sold_players  = sold_players,
        teams         = teams_list,
        recent_players= recent_players,
    )


@dashboard_bp.route("/security")
@admin_required
def security_logs():
    try:
        db = get_db()
        # Fetch logs and sort in Python to avoid index requirement
        logs_docs = db.collection("security_logs").stream()
        logs = []
        for doc in logs_docs:
            l = doc.to_dict()
            l['id'] = doc.id
            logs.append(l)
        
        # Sort by created_at DESC
        logs.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
        logs = logs[:50]
    except Exception as e:
        flash(f"Error loading security logs: {e}", "danger")
        logs = []
    return render_template("admin/security.html", logs=logs)



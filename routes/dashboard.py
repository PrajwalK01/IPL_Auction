"""routes/dashboard.py — Admin dashboard with live stats from all collections."""

from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, flash
from db.firebase import get_db
from db.helpers import get_all_players

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

        # Fetch all players from all 4 collections
        all_players = get_all_players()
        all_teams = [d.to_dict() | {"id": d.id}
                     for d in db.collection("teams").stream()]

        # Filter active
        active_players = [p for p in all_players
                          if p.get("auction_status") != "unavailable"]
        active_teams = [t for t in all_teams
                        if not t.get("is_deleted") and t.get("is_active", True)]

        total_players = len(active_players)
        total_teams = len(active_teams)

        # Aggregate purses
        total_player_purse = 0
        total_mgmt_purse = 0
        teams_list = []

        for t in active_teams:
            p_purse = float(t.get("player_purse", 0))
            m_purse = float(t.get("mgmt_purse", 0))
            total_player_purse += p_purse
            total_mgmt_purse += m_purse

            t["squad_size"] = int(t.get("squad_count", 0))
            t["player_remaining"] = p_purse - float(t.get("player_spent", 0))
            t["mgmt_remaining"] = m_purse - float(t.get("mgmt_spent", 0))
            teams_list.append(t)

        total_overall_purse = total_player_purse + total_mgmt_purse

        # Sold players count
        sold_players = len([p for p in active_players
                            if p.get("auction_status") == "sold"])

        # Auction log count
        auction_logs = list(db.collection("auction_logs").stream())
        total_bids = len(auction_logs)

        # Recent sold players
        recent_players = sorted(
            [p for p in all_players if p.get("auction_status") == "sold"],
            key=lambda x: x.get("created_at") or 0,
            reverse=True,
        )[:8]

    except Exception as e:
        flash(f"Dashboard error: {e}", "danger")
        teams_list = []
        recent_players = []
        total_players = total_teams = total_bids = sold_players = 0
        total_player_purse = total_mgmt_purse = total_overall_purse = 0

    return render_template("dashboard.html",
        username=session.get("username"),
        role=session.get("role"),
        total_players=total_players,
        total_teams=total_teams,
        total_player_purse=total_player_purse,
        total_mgmt_purse=total_mgmt_purse,
        total_overall_purse=total_overall_purse,
        total_bids=total_bids,
        sold_players=sold_players,
        teams=teams_list,
        recent_players=recent_players,
    )


@dashboard_bp.route("/security")
@admin_required
def security_logs():
    try:
        db = get_db()
        logs_docs = db.collection("security_logs").stream()
        logs = []
        for doc in logs_docs:
            log = doc.to_dict()
            log["id"] = doc.id
            logs.append(log)

        logs.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
        logs = logs[:50]
    except Exception as e:
        flash(f"Error loading security logs: {e}", "danger")
        logs = []
    return render_template("admin/security.html", logs=logs)

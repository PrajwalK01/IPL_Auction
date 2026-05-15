"""routes/team/portal.py — Team portal: dashboard, squad, bid history."""
from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, flash
from db.firebase import get_db

team_bp = Blueprint("team", __name__, url_prefix="/team")


def team_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_type") != "team":
            flash("Please log in as a team.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@team_bp.route("/dashboard")
@team_required
def dashboard():
    tid = session["team_db_id"]
    try:
        db = get_db()
        team_doc = db.collection("teams").document(tid).get()
        if not team_doc.exists or team_doc.to_dict().get("IsDeleted") == True:
            session.clear()
            flash("Team not found. Please log in again.", "warning")
            return redirect(url_for("auth.login"))
        
        team = team_doc.to_dict()
        team['id'] = tid

        # Fetch players and bids for in-memory filtering
        all_players = {d.id: d.to_dict() for d in db.collection("players").stream()}
        all_results = [d.to_dict() for d in db.collection("auction_results").stream()]
        all_bids    = [d.to_dict() for d in db.collection("bids").stream()]

        squad = [p for p in all_players.values() if p.get("sold_to_team_id") == team.get("team_id") and p.get("is_deleted") == 0]
        squad_count = len(squad)

        my_bids = [b for b in all_bids if b.get("team_id") == team.get("team_id") and b.get("is_deleted") == 0]
        bid_count = len(my_bids)

        # Recent Buys
        my_results = sorted(
            [r for r in all_results if r.get("team_id") == team.get("team_id") and r.get("is_deleted") == 0],
            key=lambda x: x.get("sold_at") or 0,
            reverse=True
        )[:5]
        
        recent_buys = []
        for rb in my_results:
            p_data = all_players.get(rb["player_id"])
            if p_data:
                rb.update({
                    "player_id": p_data["player_id"],
                    "player_name": p_data["player_name"],
                    "role": p_data["role"],
                    "nationality": p_data["nationality"]
                })
            recent_buys.append(rb)

    except Exception as e:
        flash(f"Portal error: {e}", "danger")
        team = {"team_name": "Unknown", "team_short_name": "?", "home_ground": None,
                "team_logo": None, "total_purse": 0, "spent_amount": 0, "username": "",
                "player_purse": 0, "player_spent": 0, "mgmt_purse": 0, "mgmt_spent": 0}
        squad_count = bid_count = 0
        recent_buys = []

    player_remaining = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))
    mgmt_remaining   = float(team.get("mgmt_purse", 0)) - float(team.get("mgmt_spent", 0))
    
    return render_template("team/dashboard.html",
        team        = team,
        squad_count = squad_count,
        bid_count   = bid_count,
        player_remaining = player_remaining,
        mgmt_remaining   = mgmt_remaining,
        recent_buys = recent_buys,
    )


@team_bp.route("/squad")
@team_required
def squad():
    tid = session["team_db_id"]
    try:
        db = get_db()
        team_doc = db.collection("teams").document(tid).get()
        team = team_doc.to_dict()
        team['id'] = tid

        all_players = {d.id: d.to_dict() for d in db.collection("players").stream()}
        all_results = [d.to_dict() for d in db.collection("auction_results").stream()]

        my_results = [r for r in all_results if r.get("team_id") == team.get("team_id") and r.get("is_deleted") == 0]
        players = []
        for rb in my_results:
            p_data = all_players.get(rb["player_id"])
            if p_data:
                p_copy = p_data.copy()
                p_copy.update({
                    "final_price": rb["final_price"],
                    "sold_at": rb["sold_at"]
                })
                players.append(p_copy)
        
        players.sort(key=lambda x: (x.get("role", ""), x.get("player_name", "")))

    except Exception as e:
        flash(f"Portal error: {e}", "danger")
        team = {"team_name": "", "team_short_name": "", "team_logo": None,
                "total_purse": 0, "spent_amount": 0, "username": "", "home_ground": None}
        players = []

    player_remaining = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))
    mgmt_remaining   = float(team.get("mgmt_purse", 0)) - float(team.get("mgmt_spent", 0))
    return render_template("team/squad.html", team=team, players=players, 
                           player_remaining=player_remaining, mgmt_remaining=mgmt_remaining)


@team_bp.route("/history")
@team_required
def history():
    tid = session["team_db_id"]
    try:
        db = get_db()
        team_doc = db.collection("teams").document(tid).get()
        team = team_doc.to_dict()
        team['id'] = tid

        all_players = {d.id: d.to_dict() for d in db.collection("players").stream()}
        all_bids    = [d.to_dict() for d in db.collection("bids").stream()]

        bids = sorted(
            [b for b in all_bids if b.get("team_id") == team.get("team_id") and b.get("is_deleted") == 0],
            key=lambda x: x.get("bid_time") or 0,
            reverse=True
        )

        for b in bids:
            p_data = all_players.get(b["player_id"])
            if p_data:
                b.update({
                    "player_id": p_data["player_id"],
                    "player_name": p_data["player_name"],
                    "role": p_data["role"]
                })

    except Exception as e:
        flash(f"Portal error: {e}", "danger")
        team = {"team_name": "", "team_short_name": "", "team_logo": None,
                "total_purse": 0, "spent_amount": 0, "username": "", "home_ground": None}
        bids = []

    player_remaining = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))
    mgmt_remaining   = float(team.get("mgmt_purse", 0)) - float(team.get("mgmt_spent", 0))
    return render_template("team/history.html", team=team, bids=bids, 
                           player_remaining=player_remaining, mgmt_remaining=mgmt_remaining)



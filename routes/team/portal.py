"""routes/team/portal.py — Team portal: dashboard, squad, bid history."""

from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from db.firebase import get_db
from db.helpers import get_all_players

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
        if not team_doc.exists or team_doc.to_dict().get("is_deleted"):
            session.clear()
            flash("Team not found. Please log in again.", "warning")
            return redirect(url_for("auth.login"))

        team = team_doc.to_dict()
        team["id"] = tid

        # Squad count from team doc
        squad_count = int(team.get("squad_count", 0))

        # Auction logs for this team
        all_logs = [d.to_dict() for d in db.collection("auction_logs").stream()]
        my_logs = [lg for lg in all_logs
                   if lg.get("team_id") == team.get("team_id")
                   and lg.get("outcome") == "sold"]
        my_logs.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
        recent_buys = my_logs[:5]

        bid_count = len(my_logs)

    except Exception as e:
        flash(f"Portal error: {e}", "danger")
        team = {"team_name": "Unknown", "team_short_name": "?",
                "team_logo": None, "total_purse": 0,
                "player_purse": 0, "player_spent": 0,
                "mgmt_purse": 0, "mgmt_spent": 0}
        squad_count = bid_count = 0
        recent_buys = []

    player_remaining = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))
    mgmt_remaining = float(team.get("mgmt_purse", 0)) - float(team.get("mgmt_spent", 0))

    return render_template("team/dashboard.html",
                           team=team,
                           squad_count=squad_count,
                           bid_count=bid_count,
                           player_remaining=player_remaining,
                           mgmt_remaining=mgmt_remaining,
                           recent_buys=recent_buys,
                           )


@team_bp.route("/squad")
@team_required
def squad():
    tid = session["team_db_id"]
    try:
        db = get_db()
        team_doc = db.collection("teams").document(tid).get()
        team = team_doc.to_dict()
        team["id"] = tid

        # Fetch sold players from all collections for this team
        all_players = get_all_players()
        players = [p for p in all_players
                   if p.get("sold_to_team_id") == team.get("team_id")
                   and p.get("auction_status") == "sold"]
        players.sort(key=lambda x: (x.get("player_type", ""), x.get("player_name", "")))

    except Exception as e:
        flash(f"Portal error: {e}", "danger")
        team = {"team_name": "", "team_short_name": "", "team_logo": None,
                "total_purse": 0, "player_purse": 0, "player_spent": 0,
                "mgmt_purse": 0, "mgmt_spent": 0}
        players = []

    player_remaining = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))
    mgmt_remaining = float(team.get("mgmt_purse", 0)) - float(team.get("mgmt_spent", 0))
    return render_template("team/squad.html", team=team, players=players,
                           player_remaining=player_remaining,
                           mgmt_remaining=mgmt_remaining)


@team_bp.route("/history")
@team_required
def history():
    tid = session["team_db_id"]
    try:
        db = get_db()
        team_doc = db.collection("teams").document(tid).get()
        team = team_doc.to_dict()
        team["id"] = tid

        # Fetch auction logs for this team
        all_logs = [d.to_dict() | {"id": d.id}
                    for d in db.collection("auction_logs").stream()]
        logs = sorted(
            [lg for lg in all_logs if lg.get("team_id") == team.get("team_id")],
            key=lambda x: x.get("timestamp") or 0,
            reverse=True,
        )

    except Exception as e:
        flash(f"Portal error: {e}", "danger")
        team = {"team_name": "", "team_short_name": "", "team_logo": None,
                "total_purse": 0, "player_purse": 0, "player_spent": 0,
                "mgmt_purse": 0, "mgmt_spent": 0}
        logs = []

    player_remaining = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))
    mgmt_remaining = float(team.get("mgmt_purse", 0)) - float(team.get("mgmt_spent", 0))
    return render_template("team/history.html", team=team, logs=logs,
                           player_remaining=player_remaining,
                           mgmt_remaining=mgmt_remaining)


@team_bp.route("/playing11", methods=["GET", "POST"])
@team_required
def playing11():
    tid = session["team_db_id"]
    db = get_db()
    try:
        team_doc = db.collection("teams").document(tid).get()
        team = team_doc.to_dict()
        team["id"] = tid

        # Fetch sold players belonging to this team
        all_players = get_all_players()
        players = [p for p in all_players
                   if p.get("sold_to_team_id") == team.get("team_id")
                   and p.get("auction_status") == "sold"]
        players.sort(key=lambda x: x.get("player_name", ""))

        if request.method == "POST":
            playing_xi_ids = request.form.getlist("playing_xi")
            impact_id = request.form.get("impact_player")

            if len(playing_xi_ids) > 11:
                flash("You cannot select more than 11 players for your Playing XI.", "warning")
            elif impact_id in playing_xi_ids and impact_id:
                flash("Impact Player cannot be part of the Playing XI.", "warning")
            else:
                db.collection("teams").document(tid).update({
                    "playing_11_ids": playing_xi_ids,
                    "impact_player_id": impact_id or None,
                    "playing_11_submitted": True
                })
                flash("Playing XI & Impact Player submitted successfully! 🏏", "success")
                return redirect(url_for("team.squad"))

    except Exception as e:
        flash(f"Portal error: {e}", "danger")
        players = []
        team = {"team_name": "", "team_short_name": ""}

    player_remaining = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))
    mgmt_remaining = float(team.get("mgmt_purse", 0)) - float(team.get("mgmt_spent", 0))
    
    current_xi = team.get("playing_11_ids") or []
    current_impact = team.get("impact_player_id") or ""

    return render_template("team/playing11.html", team=team, players=players,
                           player_remaining=player_remaining,
                           mgmt_remaining=mgmt_remaining,
                           current_xi=current_xi,
                           current_impact=current_impact)


@team_bp.route("/predictions", methods=["GET"])
@team_required
def predictions():
    tid = session["team_db_id"]
    db = get_db()
    try:
        team_doc = db.collection("teams").document(tid).get()
        team = team_doc.to_dict()
        team["id"] = tid

        pred_doc = db.collection("auction_state").document("standing_prediction").get()
        predictions = pred_doc.to_dict().get("standings") if pred_doc.exists else None

    except Exception as e:
        flash(f"Portal error: {e}", "danger")
        team = {"team_name": "", "team_short_name": ""}
        predictions = None

    player_remaining = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))
    mgmt_remaining = float(team.get("mgmt_purse", 0)) - float(team.get("mgmt_spent", 0))

    return render_template("team/predictions.html", team=team, predictions=predictions,
                           player_remaining=player_remaining,
                           mgmt_remaining=mgmt_remaining)

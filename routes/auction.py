"""routes/auction.py — Live Auction Logic with freeze, multi-collection, audit logs."""

from functools import wraps
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from firebase_admin import firestore
from db.firebase import get_db
from db.helpers import (get_player_by_id, get_player_collection, get_all_players,
                        log_auction_event, sanitize_input, COLLECTION_PREFIX)

auction_bp = Blueprint("auction", __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_type") != "admin":
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ── Freeze API with 0.5-second Cache ──────────────────────────────────────────
_freeze_cache = {"is_frozen": False, "expiry": 0}

@auction_bp.route("/api/freeze-status")
def freeze_status_api():
    """Lightweight endpoint polled by team portals with server-side caching."""
    global _freeze_cache
    import time
    
    if time.time() < _freeze_cache["expiry"]:
        return jsonify({"is_frozen": _freeze_cache["is_frozen"]})

    try:
        db = get_db()
        doc = db.collection("auction_state").document("freeze_status").get()
        is_frozen = False
        if doc.exists:
            is_frozen = doc.to_dict().get("is_frozen", False)
        
        # Update cache
        _freeze_cache["is_frozen"] = is_frozen
        _freeze_cache["expiry"] = time.time() + 0.5 # 500ms cache
        
        return jsonify({"is_frozen": is_frozen})
    except Exception:
        return jsonify({"is_frozen": False})


@auction_bp.route("/admin/auction/freeze", methods=["POST"])
@admin_required
def toggle_freeze():
    """Toggle the freeze state."""
    try:
        db = get_db()
        ref = db.collection("auction_state").document("freeze_status")
        doc = ref.get()
        current = doc.to_dict().get("is_frozen", False) if doc.exists else False

        ref.set({
            "is_frozen": not current,
            "frozen_by": session.get("username", "admin"),
            "frozen_at": firestore.SERVER_TIMESTAMP,
        })
        state = "frozen" if not current else "unfrozen"
        flash(f"Auction {state} successfully! ❄️", "info")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("auction.controller"))


# ── Live Screen ──────────────────────────────────────────────────────────────
@auction_bp.route("/live")
def live_view():
    """The Big Screen View for everyone."""
    try:
        db = get_db()
        state_doc = db.collection("auction_state").document("current").get()
        if not state_doc.exists:
            return render_template("auction/live_idle.html")

        state = state_doc.to_dict()
        if state.get("status") == "idle":
            return render_template("auction/live_idle.html")

        # Fetch active player from correct collection
        pid = state.get("player_id")
        player, _ = get_player_by_id(pid)
        if not player:
            return render_template("auction/live_idle.html")

        # Fetch current bidder team
        team_name = "No Bids"
        team_logo = None
        if state.get("bidder_id"):
            team_doc = db.collection("teams").document(state["bidder_id"]).get()
            if team_doc.exists:
                td = team_doc.to_dict()
                team_name = td.get("team_name")
                team_logo = td.get("team_logo")

        return render_template("auction/live_screen.html",
                               player=player, state=state,
                               team_name=team_name, team_logo=team_logo)
    except Exception as e:
        return f"Error: {e}"


# ── State API with 1-second Cache to Reduce Reads ─────────────────────────────
_state_cache = {"data": None, "expiry": 0}

@auction_bp.route("/auction/api/state")
def get_state_api():
    """Returns JSON of current auction state with server-side caching."""
    global _state_cache
    import time
    
    # Return cached data if still valid (1 second cache)
    if _state_cache["data"] and time.time() < _state_cache["expiry"]:
        return jsonify(_state_cache["data"])
        
    try:
        db = get_db()
        state_doc = db.collection("auction_state").document("current").get()
        if not state_doc.exists:
            return jsonify({"status": "idle"})

        state = state_doc.to_dict()
        if state.get("status") == "bidding":
            pid = state.get("player_id")
            player, _ = get_player_by_id(pid)
            if player:
                state["player_name"] = player.get("player_name")

            if state.get("bidder_id"):
                t_doc = db.collection("teams").document(state["bidder_id"]).get()
                if t_doc.exists:
                    td = t_doc.to_dict()
                    state["team_name"] = td.get("team_name")
                    state["team_logo"] = td.get("team_logo")

        # Update cache
        _state_cache["data"] = state
        _state_cache["expiry"] = time.time() + 1.0 # 1 second
        
        return jsonify(state)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Admin Control Panel ─────────────────────────────────────────────────────
@auction_bp.route("/admin/auction")
@admin_required
def controller():
    """Admin control panel for starting/stopping auction."""
    try:
        db = get_db()

        # Fetch available players from all collections
        all_players = get_all_players()
        available = [p for p in all_players
                     if p.get("auction_status") == "available"]
        available.sort(key=lambda x: x.get("player_id", ""))

        state = (db.collection("auction_state").document("current")
                 .get().to_dict() or {"status": "idle"})

        # Freeze status
        freeze_doc = db.collection("auction_state").document("freeze_status").get()
        is_frozen = freeze_doc.to_dict().get("is_frozen", False) if freeze_doc.exists else False

    except Exception as e:
        flash(f"Error: {e}", "danger")
        available = []
        state = {"status": "idle"}
        is_frozen = False

    return render_template("admin/auction_control.html",
                           players=available, state=state, is_frozen=is_frozen)


# ── Start Player Auction ────────────────────────────────────────────────────
@auction_bp.route("/admin/auction/start/<string:pid>", methods=["POST"])
@admin_required
def start_player(pid):
    try:
        db = get_db()
        player, collection = get_player_by_id(pid)
        if not player:
            flash("Player not found.", "warning")
            return redirect(url_for("auction.controller"))

        # Set player status to in_auction
        db.collection(collection).document(pid).update({
            "auction_status": "in_auction",
        })

        db.collection("auction_state").document("current").set({
            "player_id": pid,
            "player_collection": collection,
            "status": "bidding",
            "current_bid": player.get("base_price", 0),
            "bidder_id": None,
            "start_time": firestore.SERVER_TIMESTAMP,
        })
        return redirect(url_for("auction.controller"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("auction.controller"))


# ── Increment Bid (Admin) ───────────────────────────────────────────────────
@auction_bp.route("/admin/auction/increment", methods=["POST"])
@admin_required
def increment_bid():
    try:
        db = get_db()
        amount = float(request.form.get("amount", 0))
        state_ref = db.collection("auction_state").document("current")
        state = state_ref.get().to_dict()

        if not state or state.get("status") != "bidding":
            return redirect(url_for("auction.controller"))

        new_bid = float(state.get("current_bid", 0)) + amount
        state_ref.update({
            "current_bid": round(new_bid, 2),
            "last_bid_time": firestore.SERVER_TIMESTAMP,
        })
        return redirect(url_for("auction.controller"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("auction.controller"))


# ── Team Bid ─────────────────────────────────────────────────────────────────
@auction_bp.route("/team/place-bid", methods=["POST"])
def team_bid():
    """Allows a team to place a bid."""
    if session.get("user_type") != "team":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    team_id = session.get("team_id_str")

    try:
        db = get_db()

        # Check freeze
        freeze_doc = db.collection("auction_state").document("freeze_status").get()
        if freeze_doc.exists and freeze_doc.to_dict().get("is_frozen"):
            return jsonify({"success": False, "error": "Auction is frozen!"})

        state_ref = db.collection("auction_state").document("current")
        state = state_ref.get().to_dict()

        if not state or state.get("status") != "bidding":
            return jsonify({"success": False, "error": "No active auction"})

        # Check purse
        team_doc = db.collection("teams").document(team_id).get()
        team = team_doc.to_dict()
        rem = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))

        current = float(state.get("current_bid", 0))

        if state.get("bidder_id") is None:
            next_bid = current
        else:
            if state.get("bidder_id") == team_id:
                return jsonify({"success": False, "error": "You already hold the highest bid!"})
            next_bid = round(current + 0.10, 2)

        if rem < next_bid:
            return jsonify({"success": False, "error": "Insufficient Purse!"})

        state_ref.update({
            "current_bid": next_bid,
            "bidder_id": team_id,
            "last_bid_time": firestore.SERVER_TIMESTAMP,
        })
        return jsonify({"success": True, "new_bid": next_bid})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ── Sell Player ──────────────────────────────────────────────────────────────
@auction_bp.route("/admin/auction/sell", methods=["POST"])
@admin_required
def sell_player():
    """Finalizes the sale of the player."""
    try:
        db = get_db()
        state_ref = db.collection("auction_state").document("current")
        state = state_ref.get().to_dict()

        if not state or not state.get("bidder_id"):
            flash("No bidder found!", "warning")
            return redirect(url_for("auction.controller"))

        pid = state["player_id"]
        tid = state["bidder_id"]
        price = float(state["current_bid"])
        collection = state.get("player_collection") or get_player_collection(pid)

        # 1. Update player
        db.collection(collection).document(pid).update({
            "auction_status": "sold",
            "sold_to_team_id": tid,
            "sold_price": price,
        })

        # 2. Update team spent + squad_count
        team_ref = db.collection("teams").document(tid)
        team_data = team_ref.get().to_dict()
        new_spent = float(team_data.get("player_spent", 0)) + price
        new_squad = int(team_data.get("squad_count", 0)) + 1
        team_ref.update({
            "player_spent": round(new_spent, 2),
            "squad_count": new_squad,
        })

        # 3. Get player and team names for log
        player, _ = get_player_by_id(pid)
        player_name = player.get("player_name", pid) if player else pid
        team_name = team_data.get("team_name", tid)

        # 4. Audit log
        log_auction_event(pid, collection, player_name, tid, team_name, price, "sold")

        # 5. Reset state
        state_ref.set({"status": "idle"})

        flash(f"Player SOLD for ₹{price}Cr! 🔨", "success")
        return redirect(url_for("auction.controller"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("auction.controller"))


# ── Mark Unsold ──────────────────────────────────────────────────────────────
@auction_bp.route("/admin/auction/unsold", methods=["POST"])
@admin_required
def mark_unsold():
    """Mark the current player as unsold."""
    try:
        db = get_db()
        state_ref = db.collection("auction_state").document("current")
        state = state_ref.get().to_dict()

        if not state or state.get("status") != "bidding":
            return redirect(url_for("auction.controller"))

        pid = state["player_id"]
        collection = state.get("player_collection") or get_player_collection(pid)

        # Update player status
        db.collection(collection).document(pid).update({
            "auction_status": "unsold",
        })

        # Audit log
        player, _ = get_player_by_id(pid)
        player_name = player.get("player_name", pid) if player else pid
        log_auction_event(pid, collection, player_name, None, None, 0, "unsold")

        # Reset state
        state_ref.set({"status": "idle"})

        flash("Player marked as UNSOLD.", "info")
        return redirect(url_for("auction.controller"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("auction.controller"))


# ── Reset Auction ────────────────────────────────────────────────────────────
@auction_bp.route("/admin/auction/reset", methods=["POST"])
@admin_required
def reset_auction():
    try:
        db = get_db()

        # Reset the player status back to available if currently in auction
        state_doc = db.collection("auction_state").document("current").get()
        if state_doc.exists:
            state = state_doc.to_dict()
            pid = state.get("player_id")
            if pid:
                collection = state.get("player_collection") or get_player_collection(pid)
                if collection:
                    db.collection(collection).document(pid).update({
                        "auction_status": "available",
                    })

        db.collection("auction_state").document("current").set({"status": "idle"})
        flash("Auction reset successfully.", "info")
        return redirect(url_for("auction.controller"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("auction.controller"))

"""routes/auction.py — Live Auction Logic."""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from db.firebase import get_db
from firebase_admin import firestore
from functools import wraps

auction_bp = Blueprint("auction", __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_type") != "admin":
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

@auction_bp.route("/live")
def live_view():
    """The Big Screen View for everyone."""
    try:
        db = get_db()
        # Fetch current auction state
        state_doc = db.collection("auction_state").document("current").get()
        if not state_doc.exists:
            return render_template("auction/live_idle.html")
        
        state = state_doc.to_dict()
        if state.get("status") == "idle":
            return render_template("auction/live_idle.html")
            
        # Fetch active player details
        pid = state.get("player_id")
        player_doc = db.collection("players").document(pid).get()
        if not player_doc.exists:
             return render_template("auction/live_idle.html")
             
        player = player_doc.to_dict()
        
        # Fetch current bidder team if any
        team_name = "No Bids"
        team_logo = None
        if state.get("bidder_id"):
            team_doc = db.collection("teams").document(state.get("bidder_id")).get()
            if team_doc.exists:
                team_name = team_doc.to_dict().get("team_name")
                team_logo = team_doc.to_dict().get("team_logo")

        return render_template("auction/live_screen.html", 
                               player=player, 
                               state=state, 
                               team_name=team_name,
                               team_logo=team_logo)
    except Exception as e:
        return f"Error: {e}"

@auction_bp.route("/auction/api/state")
def get_state_api():
    """Returns JSON of current auction state."""
    try:
        db = get_db()
        state_doc = db.collection("auction_state").document("current").get()
        if not state_doc.exists:
            return {"status": "idle"}
        
        state = state_doc.to_dict()
        if state.get("status") == "bidding":
            pid = state.get("player_id")
            # We can skip fetching player info if the frontend already has it, 
            # but to be safe we'll fetch just the basic details needed by clients
            p_doc = db.collection("players").document(pid).get()
            if p_doc.exists:
                p_data = p_doc.to_dict()
                state["player_name"] = p_data.get("player_name")
                
            if state.get("bidder_id"):
                t_doc = db.collection("teams").document(state.get("bidder_id")).get()
                if t_doc.exists:
                    t_data = t_doc.to_dict()
                    state["team_name"] = t_data.get("team_name")
                    state["team_logo"] = t_data.get("team_logo")
        
        return state
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
@auction_bp.route("/admin/auction")
@admin_required
def controller():
    """Admin control panel for starting/stopping auction."""
    try:
        db = get_db()
        players = [d.to_dict() for d in db.collection("players").where("is_sold", "==", 0).where("is_deleted", "==", 0).stream()]
        state = db.collection("auction_state").document("current").get().to_dict() or {"status": "idle"}
    except Exception as e:
        flash(f"Error: {e}", "danger")
        players = []
        state = {"status": "idle"}
        
    return render_template("admin/auction_control.html", players=players, state=state)

@auction_bp.route("/admin/auction/start/<string:pid>", methods=["POST"])
@admin_required
def start_player(pid):
    try:
        db = get_db()
        player_doc = db.collection("players").document(pid).get()
        if not player_doc.exists:
            return {"success": False, "error": "Player not found"}
        
        p = player_doc.to_dict()
        db.collection("auction_state").document("current").set({
            "player_id": pid,
            "status": "bidding",
            "current_bid": p.get("base_price", 0),
            "bidder_id": None,
            "start_time": firestore.SERVER_TIMESTAMP
        })
        return redirect(url_for("auction.controller"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("auction.controller"))

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
            "last_bid_time": firestore.SERVER_TIMESTAMP
        })
        return redirect(url_for("auction.controller"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("auction.controller"))

@auction_bp.route("/team/place-bid", methods=["POST"])
def team_bid():
    """Allows a team to place a bid."""
    if session.get("user_type") != "team":
        return {"success": False, "error": "Unauthorized"}, 403
        
    team_id = session.get("team_id_str") # e.g. T-0001
    
    try:
        db = get_db()
        state_ref = db.collection("auction_state").document("current")
        state = state_ref.get().to_dict()
        
        if not state or state.get("status") != "bidding":
            return {"success": False, "error": "No active auction"}
            
        # Check if team has enough purse (Simple check for now)
        team_doc = db.collection("teams").document(team_id).get()
        team = team_doc.to_dict()
        rem = float(team.get("player_purse", 0)) - float(team.get("player_spent", 0))
        
        current = float(state.get("current_bid", 0))
        
        if state.get("bidder_id") is None:
            # First bid matches base price exactly
            next_bid = current
        else:
            if state.get("bidder_id") == team_id:
                return {"success": False, "error": "You already hold the highest bid!"}
            # Subsequent bids increment by 10L
            next_bid = round(current + 0.10, 2)
        
        if rem < next_bid:
            return {"success": False, "error": "Insufficient Purse!"}

        state_ref.update({
            "current_bid": next_bid,
            "bidder_id": team_id,
            "last_bid_time": firestore.SERVER_TIMESTAMP
        })
        return {"success": True, "new_bid": next_bid}
    except Exception as e:
        return {"success": False, "error": str(e)}

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
        
        # 1. Update Player
        db.collection("players").document(pid).update({
            "is_sold": 1,
            "sold_to_team_id": tid,
            "sold_price": price
        })
        
        # 2. Update Team Spent
        team_ref = db.collection("teams").document(tid)
        team_data = team_ref.get().to_dict()
        new_spent = float(team_data.get("player_spent", 0)) + price
        team_ref.update({"player_spent": round(new_spent, 2)})
        
        # 3. Add to Auction Results
        db.collection("auction_results").add({
            "player_id": pid,
            "team_id": tid,
            "final_price": price,
            "sold_at": firestore.SERVER_TIMESTAMP
        })
        
        # 4. Reset State
        state_ref.set({"status": "idle"})
        
        flash(f"Player SOLD for ₹{price}Cr! 🔨", "success")
        return redirect(url_for("auction.controller"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("auction.controller"))

@auction_bp.route("/admin/auction/reset", methods=["POST"])
@admin_required
def reset_auction():
    try:
        db = get_db()
        db.collection("auction_state").document("current").set({"status": "idle"})
        flash("Auction reset successfully.", "info")
        return redirect(url_for("auction.controller"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("auction.controller"))

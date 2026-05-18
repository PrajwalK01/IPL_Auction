import os
import random
import requests
import json
from db.firebase import get_db
from db.helpers import get_all_players

def run_ai_simulation():
    db = get_db()
    
    # 1. Fetch all active teams
    teams_docs = db.collection("teams").stream()
    teams = []
    for doc in teams_docs:
        t = doc.to_dict()
        if t.get("is_deleted") or not t.get("is_active", True):
            continue
        t["id"] = doc.id
        teams.append(t)
        
    if not teams:
        return {"error": "No active teams found to simulate."}
        
    # 2. Fetch all sold players
    all_players = get_all_players()
    sold_players = [p for p in all_players if p.get("auction_status") == "sold" and p.get("sold_to_team_id")]
    
    # Organize players by team
    team_players = {}
    for p in sold_players:
        tid = p.get("sold_to_team_id")
        if tid not in team_players:
            team_players[tid] = []
        team_players[tid].append(p)
        
    # 3. Calculate rating for each team
    team_ratings = {}
    for t in teams:
        tid = t["id"]
        t_players = team_players.get(t.get("team_id"), [])
        
        # Get Playing 11 IDs
        playing_xi_ids = t.get("playing_11_ids") or []
        impact_id = t.get("impact_player_id")
        
        # Filter playing XI players
        xi_players = [p for p in t_players if p.get("player_id") in playing_xi_ids]
        if not xi_players:
            # Fallback to top 11 players by price if no Playing XI submitted
            sorted_players = sorted(t_players, key=lambda x: float(x.get("sold_price") or 0), reverse=True)
            xi_players = sorted_players[:11]
            
        impact_player = next((p for p in t_players if p.get("player_id") == impact_id), None)
        
        # Core Rating Variables
        batting_power = 60.0
        bowling_power = 60.0
        balance_index = 50.0
        star_players = []
        
        # Calculate stats
        for p in xi_players:
            p_type = p.get("player_type", "").lower()
            sold_price = float(p.get("sold_price") or 0)
            
            if sold_price >= 1.5:
                star_players.append(p.get("player_name"))
                
            # Batting contribution
            if "batter" in p_type or "keeper" in p_type:
                sr = float(p.get("strike_rate") or 130.0)
                batting_power += (sr - 120.0) * 0.15 + (sold_price * 1.5)
            # Bowling contribution
            elif "bowler" in p_type:
                econ = float(p.get("economy") or 7.8)
                wickets = int(p.get("wickets") or 20)
                bowling_power += (8.5 - econ) * 2.0 + (wickets * 0.05) + (sold_price * 1.5)
            # All rounder contribution
            elif "round" in p_type:
                sr = float(p.get("strike_rate") or 130.0)
                econ = float(p.get("economy") or 8.0)
                batting_power += (sr - 120.0) * 0.08
                bowling_power += (8.5 - econ) * 1.0
                balance_index += 5.0
                
        # Impact player boost
        if impact_player:
            star_players.append(f"{impact_player.get('player_name')} (Impact)")
            p_type = impact_player.get("player_type", "").lower()
            if "batter" in p_type or "keeper" in p_type:
                batting_power += 5.0
            else:
                bowling_power += 5.0
                
        # Squad size correction
        squad_size = len(t_players)
        if squad_size >= 15:
            balance_index += 10.0
            
        overall_rating = (batting_power * 0.4) + (bowling_power * 0.4) + (balance_index * 0.2)
        overall_rating = min(100.0, max(40.0, overall_rating))
        
        team_ratings[tid] = {
            "team": t,
            "rating": overall_rating,
            "batting_power": batting_power,
            "bowling_power": bowling_power,
            "star_players": star_players[:3]
        }
        
    # 4. Simulate a 14-game season
    num_matches = 14
    wins = {t["id"]: 0 for t in teams}
    losses = {t["id"]: 0 for t in teams}
    nrr_points = {t["id"]: 0.0 for t in teams}
    
    # Perform matches using relative rating probabilities
    # Each team plays exactly 14 matches
    for i in range(len(teams)):
        tid1 = teams[i]["id"]
        r1 = team_ratings[tid1]["rating"]
        for j in range(num_matches):
            # Opponent choice: random other team
            opponent_idx = random.choice([idx for idx in range(len(teams)) if idx != i])
            tid2 = teams[opponent_idx]["id"]
            r2 = team_ratings[tid2]["rating"]
            
            # Probability of winning
            prob1 = r1 / (r1 + r2)
            if random.random() < prob1:
                wins[tid1] += 1
                margin = random.uniform(0.1, 1.5)
                nrr_points[tid1] += margin
            else:
                losses[tid1] += 1
                margin = random.uniform(0.1, 1.5)
                nrr_points[tid1] -= margin

    # Normalize Wins + Losses to exactly 14 per team
    for tid in wins:
        total = wins[tid] + losses[tid]
        if total != 14:
            # Rebalance
            wins[tid] = int(round((wins[tid] / total) * 14))
            losses[tid] = 14 - wins[tid]

    # Normalize Net Run Rate (sum should be close to 0)
    total_nrr = sum(nrr_points.values())
    nrr_adjustment = total_nrr / len(teams)
    for tid in nrr_points:
        nrr_points[tid] = round(nrr_points[tid] - nrr_adjustment, 3)
        if nrr_points[tid] == 0.0:
            nrr_points[tid] = round(random.uniform(-0.1, 0.1), 3)

    # 5. Generate Pundit Reviews (AI or Fallback)
    api_key = os.environ.get("GEMINI_API_KEY")
    pundit_reviews = {}
    
    for tid, info in team_ratings.items():
        t = info["team"]
        rating = info["rating"]
        stars = ", ".join(info["star_players"]) or "Roster Players"
        team_name = t.get("team_name", "Team")
        original_name = t.get("original_name") or "Generic Team"
        
        prompt = (
            f"Write a 3-sentence expert cricket pundit prediction review for the IPL team '{team_name}' "
            f"(registered as '{original_name}') with an overall balance rating of {rating:.1f}/100. "
            f"Their drafted star players are: {stars}. Assess their lineup balance and potential to win the tournament."
        )
        
        review = ""
        if api_key:
            try:
                # Call Gemini API
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                data = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                res = requests.post(url, headers=headers, json=data, timeout=5)
                if res.status_code == 200:
                    res_json = res.json()
                    review = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception:
                pass
                
        if not review:
            # Fallback highly realistic pundit reviews
            pundits = [
                f"Led by absolute giants like {stars}, {team_name} represents a highly strategic and formidable lineup that will give opponents nightmares. The depth of their Playing XI combined with excellent all-round stability makes them strong championship contenders.",
                f"The squad balance for {team_name} is outstanding. By securing star players like {stars}, they have addressed both death-bowling and top-order firepower perfectly. Expect them to dictate terms in the playoff stages.",
                f"While {team_name} has explosive potential in key departments with {stars}, they might face minor consistency issues in the middle overs. However, if their key stars fire, they are comfortably capable of a top-four finish.",
                f"A robust roster selection that showcases great auction management! With key figures like {stars} holding the fort, {team_name} displays the tactical flexibility needed to thrive under pressure in crucial matches."
            ]
            review = random.choice(pundits)
            
        pundit_reviews[tid] = review
        
    # 6. Compile Standings Table
    standings = []
    for tid, info in team_ratings.items():
        t = info["team"]
        standings.append({
            "team_id": tid,
            "team_name": t.get("team_name"),
            "team_short_name": t.get("team_short_name", "TEAM"),
            "team_logo": t.get("team_logo"),
            "original_name": t.get("original_name"),
            "matches": 14,
            "wins": wins[tid],
            "losses": losses[tid],
            "points": wins[tid] * 2,
            "nrr": nrr_points[tid],
            "rating": round(info["rating"], 1),
            "review": pundit_reviews[tid]
        })
        
    # Sort standings by points, then NRR
    standings.sort(key=lambda x: (x["points"], x["nrr"]), reverse=True)
    
    # Save simulation results in Firestore
    simulation_doc = {
        "standings": standings,
        "last_updated": firestore.SERVER_TIMESTAMP
    }
    db.collection("auction_state").document("standing_prediction").set(simulation_doc)
    
    return standings

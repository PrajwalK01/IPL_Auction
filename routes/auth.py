"""routes/auth.py — Unified login: checks users table then teams table."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from db.firebase import get_db
from db.helpers import log_security_event

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in — redirect to correct dashboard
    if session.get("user_type") == "admin":
        return redirect(url_for("dashboard.index"))
    if session.get("user_type") == "team":
        return redirect(url_for("team.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "warning")
            return render_template("login.html")

        try:
            db = get_db()

            # 1️⃣ Check admin/staff users table (NEW SCHEMA)
            users_ref = db.collection("users")
            user_docs = users_ref.where("UserName", "==", username).where("IsDelected", "==", False).limit(1).get()

            if user_docs:
                user = user_docs[0].to_dict()
                user['id'] = user_docs[0].id
                
                # PLAIN TEXT COMPARISON as requested
                if user.get("Password") == password:
                    if not user.get("IsActive", True):
                        log_security_event("LOGIN_INACTIVE", username, "fail", request)
                        flash("Your account is inactive. Contact admin.", "danger")
                        return render_template("login.html")
                    
                    session.clear()
                    session.update(
                        user_id   = user["id"],
                        username  = user["UserName"],
                        role      = user.get("UserRole", "admin"),
                        user_type = "admin"
                    )
                    log_security_event("LOGIN", username, "success", request)
                    flash(f"Welcome back, {user['UserName']}! 🏏", "success")
                    return redirect(url_for("dashboard.index"))
                else:
                    log_security_event("PASSWORD_MISMATCH", username, "fail", request)

            # 2️⃣ Check teams table (NEW SCHEMA)
            teams_ref = db.collection("teams")
            team_docs = teams_ref.where("username", "==", username).where("IsDeleted", "==", False).limit(1).get()

            if team_docs:
                team = team_docs[0].to_dict()
                team['id'] = team_docs[0].id
                
                # PLAIN TEXT COMPARISON
                if team.get("password") == password:
                    if not team.get("IsActive", True):
                        log_security_event("LOGIN_INACTIVE", username, "fail", request)
                        flash("Team account is inactive. Contact admin.", "danger")
                        return render_template("login.html")
                    
                    session.clear()
                    session.update(
                        team_db_id  = team["id"],
                        team_id_str = team["team_id"],
                        team_name   = team["team_name"],
                        team_logo   = team.get("team_logo"),
                        user_type   = "team"
                    )
                    log_security_event("LOGIN", username, "success", request)
                    flash(f"Welcome, {team['team_name']}! 🏏", "success")
                    return redirect(url_for("team.dashboard"))

            # Neither matched
            log_security_event("LOGIN_FAILED", username, "fail", request)
            flash("Invalid username or password.", "danger")


        except ConnectionError as e:
            flash(str(e), "danger")
        except Exception as exc:
            flash(f"Database error: {exc}", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    uname = session.get("username") or session.get("team_name") or "unknown"
    log_security_event("LOGOUT", uname, "success", request)
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))


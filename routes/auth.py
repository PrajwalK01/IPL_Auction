"""routes/auth.py — Unified login: admin users + team credentials subcollection."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db.firebase import get_db
from db.helpers import log_security_event, verify_password, sanitize_input

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in — redirect
    if session.get("user_type") == "admin":
        return redirect(url_for("dashboard.index"))
    if session.get("user_type") == "team":
        return redirect(url_for("team.dashboard"))

    if request.method == "POST":
        username = sanitize_input(request.form.get("username", "").strip())
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "warning")
            return render_template("login.html")

        try:
            db = get_db()

            # 1. Check admin/staff users collection
            # Try lowercase username first
            user_docs = (db.collection("users")
                         .where("username", "==", username)
                         .where("is_deleted", "==", False)
                         .limit(1).get())
            
            # Fallback to PascalCase UserName if not found
            if not user_docs:
                user_docs = (db.collection("users")
                             .where("UserName", "==", username)
                             .where("IsDelected", "==", False)
                             .limit(1).get())

            if user_docs:
                user = user_docs[0].to_dict()
                user["id"] = user_docs[0].id
                
                # Try multiple possible password field names
                stored_pw = user.get("password") or user.get("Password") or ""

                if verify_password(password, stored_pw):
                    if not user.get("is_active", user.get("IsActive", True)):
                        log_security_event("LOGIN_INACTIVE", username, "fail", request)
                        flash("Your account is inactive. Contact admin.", "danger")
                        return render_template("login.html")

                    session.clear()
                    session.update(
                        user_id=user["id"],
                        username=user.get("username", user.get("UserName")),
                        role=user.get("user_role", user.get("UserRole", "admin")),
                        user_type="admin",
                    )
                    log_security_event("LOGIN", username, "success", request)
                    flash(f"Welcome back, {session['username']}! 🏏", "success")
                    return redirect(url_for("dashboard.index"))
                else:
                    log_security_event("PASSWORD_MISMATCH", username, "fail", request)

            # 2. Check teams directly in the document
            team_docs = (db.collection("teams")
                         .where("username", "==", username)
                         .limit(1).get())

            if team_docs:
                team = team_docs[0].to_dict()
                team["id"] = team_docs[0].id

                # Handle missing or different field names for deletion status
                if team.get("is_deleted", team.get("IsDeleted", False)):
                    log_security_event("LOGIN_DELETED", username, "fail", request)
                    flash("This team account has been removed.", "danger")
                    return render_template("login.html")

                if verify_password(password, team.get("password", "")):
                    if not team.get("is_active", True):
                        log_security_event("LOGIN_INACTIVE", username, "fail", request)
                        flash("Team account is inactive. Contact admin.", "danger")
                        return render_template("login.html")

                    session.clear()
                    session.update(
                        team_db_id=team["id"],
                        team_id_str=team.get("team_id", team["id"]),
                        team_name=team["team_name"],
                        team_logo=team.get("team_logo"),
                        user_type="team",
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

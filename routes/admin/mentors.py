"""routes/admin/mentors.py — CRUD for Mentors and Coaches."""
import os
from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, current_app)
from werkzeug.utils import secure_filename
from db.firebase import get_db
from db.helpers import generate_mentor_id
from firebase_admin import firestore

mentors_bp = Blueprint("admin_mentors", __name__, url_prefix="/admin/mentors")

ALLOWED = {"png", "jpg", "jpeg", "webp"}

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_type") != "admin":
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

def save_photo(file):
    if not file or file.filename == "":
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        return None
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "mentors")
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(file.filename)
    file.save(os.path.join(upload_dir, filename))
    return filename

@mentors_bp.route("/")
@admin_required
def list_mentors():
    try:
        db = get_db()
        mentors_docs = db.collection("mentors").stream()
        teams_data = {d.id: d.to_dict() for d in db.collection("teams").stream()}
        
        mentors = []
        for doc in mentors_docs:
            m = doc.to_dict()
            if m.get("IsDeleted"): continue
            m['id'] = doc.id
            if m.get("team_id"):
                team = teams_data.get(m["team_id"])
                if team:
                    m["team_name"] = team.get("team_name")
                    m["team_short_name"] = team.get("team_short_name")
            mentors.append(m)
            
        mentors.sort(key=lambda x: x.get("mentor_id", ""))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        mentors = []
    return render_template("admin/mentors.html", mentors=mentors)

@mentors_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_mentor():
    db = get_db()
    if request.method == "POST":
        f = request.form
        mid = generate_mentor_id()
        photo = save_photo(request.files.get("photo"))
        salary = float(f.get("salary", 0))
        tid = f.get("team_id")
        
        try:
            db.collection("mentors").document(mid).set({
                "mentor_id": mid,
                "name": f["name"],
                "role": f["role"],
                "team_id": tid,
                "salary": salary,
                "photo": photo,
                "IsActive": True,
                "IsDeleted": False,
                "CreatedDate": firestore.SERVER_TIMESTAMP
            })
            
            # Update Team Mgmt Purse
            if tid:
                t_ref = db.collection("teams").document(tid)
                t_data = t_ref.get().to_dict()
                new_spent = float(t_data.get("mgmt_spent", 0)) + salary
                t_ref.update({"mgmt_spent": round(new_spent, 2)})
                
            flash(f"Mentor {mid} added successfully! ✅", "success")
            return redirect(url_for("admin_mentors.list_mentors"))
        except Exception as e:
            flash(str(e), "danger")
            
    teams = [d.to_dict() for d in db.collection("teams").where("IsDeleted", "==", False).stream()]
    return render_template("admin/mentor_form.html", mentor=None, action="Add", teams=teams)

@mentors_bp.route("/<string:mid>/delete", methods=["POST"])
@admin_required
def delete_mentor(mid):
    try:
        db = get_db()
        m_ref = db.collection("mentors").document(mid)
        m_data = m_ref.get().to_dict()
        
        # Reverse the salary from team mgmt_spent if linked
        tid = m_data.get("team_id")
        if tid:
            t_ref = db.collection("teams").document(tid)
            t_data = t_ref.get().to_dict()
            new_spent = float(t_data.get("mgmt_spent", 0)) - float(m_data.get("salary", 0))
            t_ref.update({"mgmt_spent": max(0, round(new_spent, 2))})
            
        m_ref.update({"IsDeleted": True})
        flash("Mentor removed.", "info")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("admin_mentors.list_mentors"))

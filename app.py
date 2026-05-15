"""app.py — Flask entry point. Registers all blueprints."""
from flask import Flask, redirect, url_for, render_template
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

# ── Blueprints ──────────────────────────────────────────────────────────────────
from routes.auth          import auth_bp
from routes.dashboard     import dashboard_bp
from routes.admin.teams   import teams_bp
from routes.admin.players import players_bp
from routes.admin.mentors import mentors_bp
from routes.team.portal   import team_bp
from routes.auction       import auction_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(teams_bp)
app.register_blueprint(players_bp)
app.register_blueprint(mentors_bp)
app.register_blueprint(team_bp)
app.register_blueprint(auction_bp)


@app.route("/")
def root():
    return redirect(url_for("auth.login"))


# ── Error Handlers ──────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("errors/500.html"), 500


@app.errorhandler(413)
def file_too_large(e):
    from flask import flash, redirect, request
    flash("File too large. Maximum upload size is 5MB.", "danger")
    return redirect(request.referrer or url_for("auth.login"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

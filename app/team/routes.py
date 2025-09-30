# At top of file
from flask import Blueprint, render_template, request, redirect, url_for
from ..db import get_db, seed_if_empty

bp = Blueprint("team", __name__)

# Existing index() keeps query-string support
@bp.route("/")
def index():
    seed_if_empty()
    team_code = request.args.get("code")
    game_id = request.args.get("game", 1)
    if not team_code:
        return redirect(url_for("team.lobby"))  # go to lobby if no code
    db = get_db()
    team = db.execute(
        "SELECT * FROM teams WHERE game_id = ? AND code = ?",
        (game_id, team_code)
    ).fetchone()
    if not team:
        return render_template("team.html", error=f"Team {team_code} not found in game {game_id}")
    settings = db.execute(
        "SELECT current_question_id FROM settings WHERE game_id = ?",
        (game_id,)
    ).fetchone()
    initial_qid = settings["current_question_id"] if settings else None
    ctx = {
        "gameId": int(game_id),
        "teamCode": team["code"],
        "teamName": team["name"],
        "teamId": team["id"],
        "initialQuestionId": initial_qid,
    }
    return render_template("team.html", **ctx)

# NEW: pretty URL like /team/TEAM_01
@bp.route("/<code>")
def by_code(code):
    seed_if_empty()
    game_id = 1  # or read from querystring/path if you run multiple games
    db = get_db()
    team = db.execute(
        "SELECT * FROM teams WHERE game_id = ? AND code = ?",
        (game_id, code.upper())
    ).fetchone()
    if not team:
        return render_template("team.html", error=f"Team {code} not found in game {game_id}")
    settings = db.execute(
        "SELECT current_question_id FROM settings WHERE game_id = ?",
        (game_id,)
    ).fetchone()
    initial_qid = settings["current_question_id"] if settings else None
    ctx = {
        "gameId": int(game_id),
        "teamCode": team["code"],
        "teamName": team["name"],
        "teamId": team["id"],
        "initialQuestionId": initial_qid,
    }
    return render_template("team.html", **ctx)

# Optional: a simple lobby that lists all teams and links
@bp.route("/lobby")
def lobby():
    seed_if_empty()
    db = get_db()
    game = db.execute("SELECT id FROM games ORDER BY id ASC LIMIT 1").fetchone()
    if not game:
        return render_template("team.html", error="No game found")
    teams = db.execute("SELECT name, code FROM teams WHERE game_id = ? ORDER BY id", (game["id"],)).fetchall()
    return render_template("team_lobby.html", teams=teams, gameId=game["id"])

from flask import Blueprint, render_template, request, redirect, url_for
from ..db import get_db, seed_if_empty
from .. import socketio
import time

bp = Blueprint("admin", __name__)

def game_room(game_id: int) -> str:
    """Socket.IO room name for a game."""
    return f"game:{game_id}"

def _broadcast_state(game_id: int) -> None:
    """Build and emit the current game state to all clients in the game room."""
    db = get_db()
    s = db.execute("SELECT * FROM settings WHERE game_id = ?", (game_id,)).fetchone()
    if not s:
        return

    payload = {
        "gameId": game_id,
        "state": s["state"],
        "deadlineEpochMs": s["deadline_epoch_ms"],
        "activeTeamId": s["active_team_id"],
    }

    if s["current_question_id"]:
        q = db.execute("SELECT * FROM questions WHERE id = ?", (s["current_question_id"],)).fetchone()
        if q:
            payload["question"] = {
                "id": q["id"],
                "text": q["text"],
                "options": [q["opt_a"], q["opt_b"], q["opt_c"], q["opt_d"]],
                "type": q["type"],
            }

    # Use socketio.emit (not emit) from HTTP context
    socketio.emit("state_update", payload, to=game_room(game_id))

@bp.route("/")
def index():
    """Admin console."""
    seed_if_empty()
    db = get_db()

    game = db.execute("SELECT * FROM games ORDER BY id ASC LIMIT 1").fetchone()
    if not game:
        return render_template("admin.html", error="No game found")

    gid = game["id"]
    settings = db.execute("SELECT * FROM settings WHERE game_id = ?", (gid,)).fetchone()
    rounds = db.execute("SELECT * FROM rounds WHERE game_id = ? ORDER BY order_index", (gid,)).fetchall()
    questions = db.execute("SELECT * FROM questions WHERE game_id = ?", (gid,)).fetchall()
    teams = db.execute("SELECT * FROM teams WHERE game_id = ?", (gid,)).fetchall()

    return render_template(
        "admin.html",
        game=game,
        settings=settings,
        rounds=rounds,
        questions=questions,
        teams=teams,
    )

@bp.route("/action", methods=["POST"])
def admin_action():
    """Handle admin POST actions, then broadcast and PRG back to index."""
    db = get_db()

    game = db.execute("SELECT * FROM games ORDER BY id ASC LIMIT 1").fetchone()
    if not game:
        return redirect(url_for("admin.index"))

    gid = game["id"]
    op = request.form.get("op", "").strip()
    now_ms = int(time.time() * 1000)

    if op == "set_round":
        rid = request.form.get("round_id")
        if rid:
            db.execute("UPDATE settings SET current_round_id = ? WHERE game_id = ?", (rid, gid))
            db.commit()

    elif op == "set_question":
        qid = request.form.get("question_id")
        seconds_raw = request.form.get("seconds", "30")
        if qid:
            try:
                seconds = max(1, int(seconds_raw))
                deadline = now_ms + seconds * 1000

                # Clear any accepted buzz for this question; reset active team
                db.execute(
                    "DELETE FROM buzzer_events WHERE game_id = ? AND question_id = ? AND accepted = 1",
                    (gid, qid),
                )
                db.execute(
                    "UPDATE settings "
                    "SET current_question_id = ?, state = ?, deadline_epoch_ms = ?, active_team_id = NULL "
                    "WHERE game_id = ?",
                    (qid, "SHOW", deadline, gid),
                )
                db.commit()
            except ValueError:
                pass

    elif op == "set_state":
        new_state = request.form.get("state", "").strip()
        if new_state in ("IDLE", "SHOW", "LOCK", "REVEAL"):
            db.execute("UPDATE settings SET state = ? WHERE game_id = ?", (new_state, gid))
            db.commit()

    elif op == "start_timer":
        seconds_raw = request.form.get("seconds", "30")
        try:
            seconds = max(1, int(seconds_raw))
            deadline = now_ms + seconds * 1000
            db.execute("UPDATE settings SET deadline_epoch_ms = ? WHERE game_id = ?", (deadline, gid))
            db.commit()
        except ValueError:
            pass

    elif op == "add_time":
        seconds_raw = request.form.get("seconds", "10")
        try:
            seconds = max(1, int(seconds_raw))
            row = db.execute("SELECT deadline_epoch_ms FROM settings WHERE game_id = ?", (gid,)).fetchone()
            if row and row["deadline_epoch_ms"]:
                new_deadline = row["deadline_epoch_ms"] + seconds * 1000
                db.execute("UPDATE settings SET deadline_epoch_ms = ? WHERE game_id = ?", (new_deadline, gid))
                db.commit()
        except ValueError:
            pass

    elif op == "unlock_buzz":
        s = db.execute("SELECT current_question_id FROM settings WHERE game_id = ?", (gid,)).fetchone()
        if s and s["current_question_id"]:
            db.execute(
                "DELETE FROM buzzer_events WHERE game_id = ? AND question_id = ? AND accepted = 1",
                (gid, s["current_question_id"]),
            )
            db.execute("UPDATE settings SET active_team_id = NULL WHERE game_id = ?", (gid,))
            db.commit()

    elif op == "clear_masks":
        s = db.execute("SELECT current_question_id FROM settings WHERE game_id = ?", (gid,)).fetchone()
        if s and s["current_question_id"]:
            db.execute("DELETE FROM team_masks WHERE game_id = ? AND question_id = ?", (gid, s["current_question_id"]))
            db.commit()

    elif op == "set_active_team":
        team_id_raw = request.form.get("team_id", "").strip()
        team_id = None if team_id_raw in ("", "0") else team_id_raw
        db.execute("UPDATE settings SET active_team_id = ? WHERE game_id = ?", (team_id, gid))
        db.commit()

    elif op == "add_team":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()
        if name and code:
            db.execute("INSERT INTO teams (game_id, name, code) VALUES (?, ?, ?)", (gid, name, code))
            db.commit()

    elif op == "broadcast":
        # No DB mutations; just broadcast below.
        pass

    # Notify clients
    _broadcast_state(gid)
    socketio.emit("toast", {"msg": f"Admin: {op} applied"}, to=game_room(gid))

    # PRG
    return redirect(url_for("admin.index"))

import random
import time
from flask_socketio import emit, join_room, leave_room
from . import socketio
from .db import get_db

# ----------------------------
# Room helpers
# ----------------------------
def game_room(game_id: int) -> str:
    return f"game:{game_id}"

def team_room(game_id: int, team_code: str) -> str:
    return f"game:{game_id}:team:{team_code}"

# ----------------------------
# DB helpers
# ----------------------------
def get_team_by_code(game_id: int, team_code: str):
    db = get_db()
    return db.execute(
        "SELECT * FROM teams WHERE game_id = ? AND code = ?",
        (game_id, team_code)
    ).fetchone()

def get_game_settings(game_id: int):
    db = get_db()
    return db.execute(
        "SELECT * FROM settings WHERE game_id = ?",
        (game_id,)
    ).fetchone()

def get_current_question(game_id: int):
    db = get_db()
    return db.execute(
        """
        SELECT q.*
        FROM questions q
        JOIN settings s ON q.id = s.current_question_id
        WHERE s.game_id = ?
        """,
        (game_id,)
    ).fetchone()

def get_team_masks(game_id: int, team_id: int, question_id: int):
    db = get_db()
    return db.execute(
        "SELECT masked_i1, masked_i2 FROM team_masks WHERE game_id = ? AND team_id = ? AND question_id = ?",
        (game_id, team_id, question_id)
    ).fetchone()

# ----------------------------
# Broadcast shared state
# ----------------------------
def _broadcast_state(game_id: int) -> None:
    db = get_db()
    s = get_game_settings(game_id)
    if not s:
        return

    payload = {
        "gameId": game_id,
        "state": s["state"],
        "deadlineEpochMs": s["deadline_epoch_ms"],
        "activeTeamId": s["active_team_id"],
        "currentRoundId": s["current_round_id"],
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

    active = None
    if s["active_team_id"]:
        t = db.execute("SELECT id, name, code FROM teams WHERE id = ?", (s["active_team_id"],)).fetchone()
        if t:
            active = {"id": t["id"], "name": t["name"], "code": t["code"]}
    payload["activeTeam"] = active

    socketio.emit("state_update", payload, to=game_room(game_id))

# ----------------------------
# Socket.IO handlers
# ----------------------------
@socketio.on("join")
def handle_join(data):
    game_id = data.get("gameId")
    team_code = data.get("teamCode")
    role = data.get("role", "team")

    if not game_id:
        emit("error", {"message": "Game ID required"})
        return

    join_room(game_room(game_id))

    if team_code:
        team = get_team_by_code(game_id, team_code)
        if not team:
            emit("error", {"message": "Invalid team code"})
            return
        join_room(team_room(game_id, team_code))

    emit("joined", {"gameId": game_id, "teamCode": team_code, "role": role})
    _broadcast_state(game_id)

@socketio.on("state_request")
def handle_state_request(data):
    game_id = data.get("GameId") or data.get("gameId")
    if game_id:
        _broadcast_state(game_id)

@socketio.on("buzz")
def handle_buzz(data):
    game_id = data.get("gameId")
    team_code = data.get("teamCode")

    if not game_id or not team_code:
        emit("error", {"message": "Game ID and team code required"})
        return

    db = get_db()
    team = get_team_by_code(game_id, team_code)
    if not team:
        emit("error", {"message": "Invalid team"})
        return

    s = get_game_settings(game_id)
    if not s or s["state"] != "SHOW":
        emit("error", {"message": "Buzzing not allowed in current state"})
        return

    qid = s["current_question_id"]
    if not qid:
        emit("error", {"message": "No current question"})
        return

    now_ms = int(time.time() * 1000)

    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "INSERT INTO buzzer_events (game_id, team_id, question_id, ts, accepted) VALUES (?, ?, ?, ?, 1)",
            (game_id, team["id"], qid, now_ms),
        )
        db.execute("UPDATE settings SET active_team_id = ? WHERE game_id = ?", (team["id"], game_id))
        db.commit()
    except Exception as e:
        db.rollback()
        if "UNIQUE constraint failed" in str(e):
            emit("error", {"message": "Another team buzzed first"})
        else:
            emit("error", {"message": "Buzz failed due to system error"})
        return

    socketio.emit(
        "buzz_lock",
        {"questionId": qid, "winnerTeamCode": team_code, "winnerTeamName": team["name"]},
        to=game_room(game_id),
    )

@socketio.on("fifty_request")
def handle_fifty_fifty(data):
    game_id = data.get("gameId")
    team_code = data.get("teamCode")

    if not game_id or not team_code:
        emit("error", {"message": "Game ID and team code required"})
        return

    db = get_db()
    team = get_team_by_code(game_id, team_code)
    if not team:
        emit("error", {"message": "Invalid team"})
        return

    s = get_game_settings(game_id)
    if not s or s["state"] != "SHOW":
        emit("error", {"message": "50-50 not allowed in current state"})
        return

    qid = s["current_question_id"]
    if not qid:
        emit("error", {"message": "No current question"})
        return

    q = db.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
    if not q or q["type"] != "MCQ":
        emit("error", {"message": "50-50 only available for multiple choice questions"})
        return

    existing_mask = db.execute(
        "SELECT masked_i1, masked_i2 FROM team_masks WHERE game_id = ? AND team_id = ? AND question_id = ?",
        (game_id, team["id"], qid),
    ).fetchone()
    if existing_mask:
        masked = [existing_mask["masked_i1"], existing_mask["masked_i2"]]
        socketio.emit(
            "mask_applied",
            {"gameId": game_id, "teamCode": team_code, "questionId": qid, "maskedOptions": masked},
            to=team_room(game_id, team_code),
        )
        return

    used = db.execute(
        "SELECT 1 FROM lifeline_usage WHERE game_id=? AND team_id=? AND lifeline=? AND used_in_round_id=?",
        (game_id, team["id"], "FIFTY_FIFTY", s["current_round_id"]),
    ).fetchone()
    if used:
        emit("error", {"message": "50-50 lifeline already used this round"})
        return

    correct = q["correct_index"]
    wrong = [i for i in range(4) if i != correct]
    seed = f"{game_id}:{team_code}:{qid}"
    rng = random.Random(seed)
    masked = sorted(rng.sample(wrong, 2))

    now_ms = int(time.time() * 1000)
    db.execute(
        "INSERT INTO team_masks (game_id, team_id, question_id, masked_i1, masked_i2, ts) VALUES (?, ?, ?, ?, ?, ?)",
        (game_id, team["id"], qid, masked[0], masked[1], now_ms),
    )
    db.execute(
        "INSERT INTO lifeline_usage (game_id, team_id, lifeline, used_in_round_id, used_at) VALUES (?, ?, ?, ?, ?)",
        (game_id, team["id"], "FIFTY_FIFTY", s["current_round_id"], now_ms),
    )
    db.commit()

    socketio.emit(
        "mask_applied",
        {"gameId": game_id, "teamCode": team_code, "questionId": qid, "maskedOptions": masked},
        to=team_room(game_id, team_code),
    )

@socketio.on("state_push")
def handle_state_push(data):
    game_id = data.get("gameId")
    if game_id:
        _broadcast_state(game_id)

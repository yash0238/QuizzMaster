from flask import Blueprint, render_template, request
from ..db import get_db, seed_if_empty

bp = Blueprint('team', __name__)

@bp.route("/lobby")
def lobby():
    from ..db import get_db, seed_if_empty
    seed_if_empty()
    db = get_db()
    game = db.execute("SELECT id FROM games ORDER BY id ASC LIMIT 1").fetchone()
    if not game:
        return render_template("team.html", error="No game found")
    teams = db.execute("SELECT name, code FROM teams WHERE game_id=? ORDER BY id ASC", (game["id"],)).fetchall()
    return render_template("team_lobby.html", teams=teams, gameId=game["id"])

@bp.route('/')
def index():
    """Team view - accepts team code and displays team interface"""
    # Ensure demo data exists
    seed_if_empty()
    
    team_code = request.args.get('code')
    game_id = request.args.get('game', 1)  # Default to game 1
    
    if not team_code:
        return redirect(url_for("team.lobby"))
    
    db = get_db()
    
    # Validate team exists in game
    team = db.execute(
        'SELECT * FROM teams WHERE game_id = ? AND code = ?',
        (game_id, team_code)
    ).fetchone()
    
    if not team:
        return render_template('team.html', error=f"Team '{team_code}' not found in game {game_id}")
    
    # Get current question ID
    settings = db.execute('SELECT current_question_id FROM settings WHERE game_id = ?', (game_id,)).fetchone()
    initial_question_id = settings['current_question_id'] if settings else None
    
    # Prepare context
    context = {
        'gameId': int(game_id),
        'teamCode': team_code,
        'teamName': team['name'],
        'teamId': team['id'],
        'initialQuestionId': initial_question_id
    }
    
    return render_template('team.html', **context)

from flask import Blueprint, render_template, current_app
from ..db import get_db, seed_if_empty

bp = Blueprint('host', __name__)

@bp.route('/')
def index():
    """Host view - displays current question, timer, and game state"""
    # Ensure demo data exists
    seed_if_empty()
    
    db = get_db()
    
    # Get the first game (demo game)
    game = db.execute('SELECT * FROM games ORDER BY id LIMIT 1').fetchone()
    if not game:
        return render_template('host.html', error="No game found")
    
    game_id = game['id']
    
    # Get current settings
    settings = db.execute('SELECT * FROM settings WHERE game_id = ?', (game_id,)).fetchone()
    
    # Build initial state
    initial_state = {
        'gameId': game_id,
        'state': settings['state'] if settings else 'IDLE',
        'deadlineEpochMs': settings['deadline_epoch_ms'] if settings else 0,
        'activeTeamId': settings['active_team_id'] if settings else None
    }
    
    # Add question data if available
    if settings and settings['current_question_id']:
        question = db.execute(
            'SELECT * FROM questions WHERE id = ?',
            (settings['current_question_id'],)
        ).fetchone()
        
        if question:
            initial_state['question'] = {
                'id': question['id'],
                'text': question['text'],
                'options': [
                    question['opt_a'],
                    question['opt_b'],
                    question['opt_c'],
                    question['opt_d']
                ],
                'type': question['type']
            }
    
    return render_template('host.html', initial_state=initial_state)
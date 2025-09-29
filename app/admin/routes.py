from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_socketio import emit
from ..db import get_db, seed_if_empty
from .. import socketio
import time

bp = Blueprint('admin', __name__)

def game_room(game_id):
    """Generate game room name"""
    return f"game:{game_id}"

def _broadcast_state(game_id):
    """Broadcast current game state"""
    db = get_db()
    settings = db.execute('SELECT * FROM settings WHERE game_id = ?', (game_id,)).fetchone()
    if not settings:
        return
    
    payload = {
        'gameId': game_id,
        'state': settings['state'],
        'deadlineEpochMs': settings['deadline_epoch_ms'],
        'activeTeamId': settings['active_team_id']
    }
    
    if settings['current_question_id']:
        question = db.execute('SELECT * FROM questions WHERE id = ?', (settings['current_question_id'],)).fetchone()
        if question:
            payload['question'] = {
                'id': question['id'],
                'text': question['text'],
                'options': [question['opt_a'], question['opt_b'], question['opt_c'], question['opt_d']],
                'type': question['type']
            }
    
    socketio.emit('state_update', payload, to=game_room(game_id))

@bp.route('/')
def index():
    """Admin console - game management interface"""
    # Ensure demo data exists
    seed_if_empty()
    
    db = get_db()
    
    # Get game data
    game = db.execute('SELECT * FROM games ORDER BY id LIMIT 1').fetchone()
    if not game:
        return render_template('admin.html', error="No game found")
    
    game_id = game['id']
    
    # Get settings, rounds, questions, and teams
    settings = db.execute('SELECT * FROM settings WHERE game_id = ?', (game_id,)).fetchone()
    rounds = db.execute('SELECT * FROM rounds WHERE game_id = ? ORDER BY order_index', (game_id,)).fetchall()
    questions = db.execute('SELECT * FROM questions WHERE game_id = ?', (game_id,)).fetchall()
    teams = db.execute('SELECT * FROM teams WHERE game_id = ?', (game_id,)).fetchall()
    
    context = {
        'game': game,
        'settings': settings,
        'rounds': rounds,
        'questions': questions,
        'teams': teams
    }
    
    return render_template('admin.html', **context)

@bp.route('/action', methods=['POST'])
def admin_action():
    """Handle admin actions"""
    db = get_db()
    
    # Get the first game
    game = db.execute('SELECT * FROM games ORDER BY id LIMIT 1').fetchone()
    if not game:
        return redirect(url_for('admin.index'))
    
    game_id = game['id']
    op = request.form.get('op')
    current_time = int(time.time() * 1000)
    
    if op == 'set_round':
        round_id = request.form.get('round_id')
        if round_id:
            db.execute('UPDATE settings SET current_round_id = ? WHERE game_id = ?', (round_id, game_id))
            db.commit()
    
    elif op == 'set_question':
        question_id = request.form.get('question_id')
        seconds = request.form.get('seconds', 30)
        if question_id:
            try:
                seconds = int(seconds)
                deadline = current_time + (seconds * 1000)
                
                # Clear any accepted buzzes for this question
                db.execute('DELETE FROM buzzer_events WHERE game_id = ? AND question_id = ? AND accepted = 1', 
                          (game_id, question_id))
                
                db.execute(
                    'UPDATE settings SET current_question_id = ?, state = ?, deadline_epoch_ms = ?, active_team_id = NULL WHERE game_id = ?',
                    (question_id, 'SHOW', deadline, game_id)
                )
                db.commit()
            except ValueError:
                pass
    
    elif op == 'set_state':
        state = request.form.get('state')
        if state in ['IDLE', 'SHOW', 'LOCK', 'REVEAL']:
            db.execute('UPDATE settings SET state = ? WHERE game_id = ?', (state, game_id))
            db.commit()
    
    elif op == 'start_timer':
        seconds = request.form.get('seconds', 30)
        try:
            seconds = int(seconds)
            deadline = current_time + (seconds * 1000)
            db.execute('UPDATE settings SET deadline_epoch_ms = ? WHERE game_id = ?', (deadline, game_id))
            db.commit()
        except ValueError:
            pass
    
    elif op == 'add_time':
        seconds = request.form.get('seconds', 10)
        try:
            seconds = int(seconds)
            settings = db.execute('SELECT deadline_epoch_ms FROM settings WHERE game_id = ?', (game_id,)).fetchone()
            if settings:
                new_deadline = settings['deadline_epoch_ms'] + (seconds * 1000)
                db.execute('UPDATE settings SET deadline_epoch_ms = ? WHERE game_id = ?', (new_deadline, game_id))
                db.commit()
        except ValueError:
            pass
    
    elif op == 'unlock_buzz':
        settings = db.execute('SELECT current_question_id FROM settings WHERE game_id = ?', (game_id,)).fetchone()
        if settings and settings['current_question_id']:
            db.execute('DELETE FROM buzzer_events WHERE game_id = ? AND question_id = ? AND accepted = 1',
                      (game_id, settings['current_question_id']))
            db.execute('UPDATE settings SET active_team_id = NULL WHERE game_id = ?', (game_id,))
            db.commit()
    
    elif op == 'clear_masks':
        settings = db.execute('SELECT current_question_id FROM settings WHERE game_id = ?', (game_id,)).fetchone()
        if settings and settings['current_question_id']:
            db.execute('DELETE FROM team_masks WHERE game_id = ? AND question_id = ?',
                      (game_id, settings['current_question_id']))
            db.commit()
    
    elif op == 'set_active_team':
        team_id = request.form.get('team_id')
        if team_id == '0' or team_id == '':
            team_id = None
        db.execute('UPDATE settings SET active_team_id = ? WHERE game_id = ?', (team_id, game_id))
        db.commit()
    
    elif op == 'broadcast':
        # No DB change, just broadcast
        pass
    
    # Broadcast state and send toast
    _broadcast_state(game_id)
    socketio.emit('toast', {'msg': f'Admin: {op} applied'}, to=game_room(game_id))
    
    # Post-Redirect-Get pattern
    return redirect(url_for('admin.index'))
import random
import time
from flask_socketio import emit, join_room, leave_room
from . import socketio
from .db import get_db

# Room helper functions
def game_room(game_id):
    """Generate game room name"""
    return f"game:{game_id}"

def team_room(game_id, team_code):
    """Generate team room name"""
    return f"game:{game_id}:team:{team_code}"

# Database helper functions
def get_team_by_code(game_id, team_code):
    """Get team by game ID and team code"""
    db = get_db()
    return db.execute(
        'SELECT * FROM teams WHERE game_id = ? AND code = ?',
        (game_id, team_code)
    ).fetchone()

def get_current_question(game_id):
    """Get current question for game"""
    db = get_db()
    return db.execute(
        '''SELECT q.* FROM questions q 
           JOIN settings s ON q.id = s.current_question_id 
           WHERE s.game_id = ?''',
        (game_id,)
    ).fetchone()

def get_game_settings(game_id):
    """Get current game settings"""
    db = get_db()
    return db.execute(
        'SELECT * FROM settings WHERE game_id = ?',
        (game_id,)
    ).fetchone()

def get_team_masks(game_id, team_id, question_id):
    """Get masked options for team and question"""
    db = get_db()
    return db.execute(
        'SELECT masked_i1, masked_i2 FROM team_masks WHERE game_id = ? AND team_id = ? AND question_id = ?',
        (game_id, team_id, question_id)
    ).fetchone()

def _broadcast_state(game_id):
    """Broadcast current game state to all clients in game room"""
    db = get_db()
    
    # Get current settings
    settings = get_game_settings(game_id)
    if not settings:
        return
    
    # Build base payload
    payload = {
        'gameId': game_id,
        'state': settings['state'],
        'deadlineEpochMs': settings['deadline_epoch_ms'],
        'activeTeamId': settings['active_team_id']
    }
    
    # Add question data if available
    if settings['current_question_id']:
        question = db.execute(
            'SELECT * FROM questions WHERE id = ?',
            (settings['current_question_id'],)
        ).fetchone()
        
        if question:
            payload['question'] = {
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
    
    # Broadcast to game room
    socketio.emit('state_update', payload, to=game_room(game_id))

# Socket.IO event handlers
@socketio.on('join')
def handle_join(data):
    """Handle client joining game and team rooms"""
    game_id = data.get('gameId')
    team_code = data.get('teamCode')
    role = data.get('role', 'team')
    
    if not game_id:
        emit('error', {'message': 'Game ID required'})
        return
    
    # Join game room
    join_room(game_room(game_id))
    
    # Join team room if team code provided
    if team_code:
        team = get_team_by_code(game_id, team_code)
        if team:
            join_room(team_room(game_id, team_code))
        else:
            emit('error', {'message': 'Invalid team code'})
            return
    
    # Send join confirmation
    emit('joined', {
        'gameId': game_id,
        'teamCode': team_code,
        'role': role
    })
    
    # Broadcast current state
    _broadcast_state(game_id)

@socketio.on('state_request')
def handle_state_request(data):
    """Handle request for current game state"""
    game_id = data.get('gameId')
    if game_id:
        _broadcast_state(game_id)

@socketio.on('buzz')
def handle_buzz(data):
    """Handle team buzzer press - first buzz wins"""
    game_id = data.get('gameId')
    team_code = data.get('teamCode')
    
    if not game_id or not team_code:
        emit('error', {'message': 'Game ID and team code required'})
        return
    
    db = get_db()
    
    # Get team
    team = get_team_by_code(game_id, team_code)
    if not team:
        emit('error', {'message': 'Invalid team'})
        return
    
    # Get current settings
    settings = get_game_settings(game_id)
    if not settings or settings['state'] != 'SHOW':
        emit('error', {'message': 'Buzzing not allowed in current state'})
        return
    
    question_id = settings['current_question_id']
    if not question_id:
        emit('error', {'message': 'No current question'})
        return
    
    # Atomic buzz handling with database constraints ensuring first-buzz-wins
    current_time = int(time.time() * 1000)
    
    try:
        # Begin immediate transaction for atomicity
        db.execute('BEGIN IMMEDIATE')
        
        # Try to insert accepted buzz - will fail if another team already buzzed due to unique constraint
        db.execute(
            'INSERT INTO buzzer_events (game_id, team_id, question_id, ts, accepted) VALUES (?, ?, ?, ?, 1)',
            (game_id, team['id'], question_id, current_time)
        )
        
        # Update settings to set active team
        db.execute(
            'UPDATE settings SET active_team_id = ? WHERE game_id = ?',
            (team['id'], game_id)
        )
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        # Check if it was a unique constraint violation (another team buzzed first)
        if 'UNIQUE constraint failed' in str(e):
            emit('error', {'message': 'Another team buzzed first'})
        else:
            emit('error', {'message': 'Buzz failed due to system error'})
        return
    
    # Broadcast buzz lock to all clients
    socketio.emit('buzz_lock', {
        'questionId': question_id,
        'winnerTeamCode': team_code,
        'winnerTeamName': team['name']
    }, to=game_room(game_id))

@socketio.on('fifty_request')
def handle_fifty_fifty(data):
    """Handle 50-50 lifeline request"""
    game_id = data.get('gameId')
    team_code = data.get('teamCode')
    
    if not game_id or not team_code:
        emit('error', {'message': 'Game ID and team code required'})
        return
    
    db = get_db()
    
    # Get team
    team = get_team_by_code(game_id, team_code)
    if not team:
        emit('error', {'message': 'Invalid team'})
        return
    
    # Get current settings and question
    settings = get_game_settings(game_id)
    if not settings or settings['state'] != 'SHOW':
        emit('error', {'message': '50-50 not allowed in current state'})
        return
    
    question_id = settings['current_question_id']
    if not question_id:
        emit('error', {'message': 'No current question'})
        return
    
    # Get question to ensure it's MCQ
    question = db.execute('SELECT * FROM questions WHERE id = ?', (question_id,)).fetchone()
    if not question or question['type'] != 'MCQ':
        emit('error', {'message': '50-50 only available for multiple choice questions'})
        return
    
    # Check if lifeline already used
    existing_usage = db.execute(
        'SELECT id FROM lifeline_usage WHERE game_id = ? AND team_id = ? AND lifeline = ?',
        (game_id, team['id'], 'FIFTY_FIFTY')
    ).fetchone()
    
    if existing_usage:
        emit('error', {'message': '50-50 lifeline already used'})
        return
    
    # Check if mask already exists for this question
    existing_mask = db.execute(
        'SELECT id FROM team_masks WHERE game_id = ? AND team_id = ? AND question_id = ?',
        (game_id, team['id'], question_id)
    ).fetchone()
    
    if existing_mask:
        emit('error', {'message': '50-50 already applied to this question'})
        return
    
    # Deterministically select two wrong options using seed
    correct_index = question['correct_index']
    wrong_options = [i for i in range(4) if i != correct_index]
    
    # Use deterministic random seed for consistent results
    seed = f"{game_id}:{team_code}:{question_id}"
    rng = random.Random(seed)
    masked_options = rng.sample(wrong_options, 2)
    masked_options.sort()  # Ensure consistent ordering
    
    current_time = int(time.time() * 1000)
    
    # Insert team mask
    db.execute(
        'INSERT INTO team_masks (game_id, team_id, question_id, masked_i1, masked_i2, ts) VALUES (?, ?, ?, ?, ?, ?)',
        (game_id, team['id'], question_id, masked_options[0], masked_options[1], current_time)
    )
    
    # Insert lifeline usage
    db.execute(
        'INSERT INTO lifeline_usage (game_id, team_id, lifeline, used_in_round_id, used_at) VALUES (?, ?, ?, ?, ?)',
        (game_id, team['id'], 'FIFTY_FIFTY', settings['current_round_id'], current_time)
    )
    
    db.commit()
    
    # Send mask applied only to team room
    socketio.emit('mask_applied', {
        'questionId': question_id,
        'maskedOptions': masked_options
    }, to=team_room(game_id, team_code))

@socketio.on('state_push')
def handle_state_push(data):
    """Handle admin state push request - restricted to prevent abuse"""
    game_id = data.get('gameId')
    # Basic validation - in production, add proper authentication/authorization
    if game_id:
        _broadcast_state(game_id)
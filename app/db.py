import sqlite3
import click
from pathlib import Path
from flask import current_app, g
from flask.cli import with_appcontext
import time

def get_db():
    """Get database connection with row factory and foreign keys enabled"""
    if 'db' not in g:
        # Ensure instance directory exists
        instance_path = Path(current_app.instance_path)
        instance_path.mkdir(exist_ok=True)
        
        # Open connection with proper settings
        g.db = sqlite3.connect(
            current_app.config['DB_PATH'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    
    return g.db

def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(schema_path=None):
    """Initialize database with schema from migrations/schema.sql"""
    db = get_db()
    
    if schema_path is None:
        schema_path = Path(__file__).parent.parent / 'migrations' / 'schema.sql'
    
    with open(schema_path, 'r') as f:
        db.executescript(f.read())
    
    db.commit()

def seed_if_empty():
    """Insert demo data if no games exist"""
    db = get_db()
    
    # Check if any games exist
    existing_games = db.execute('SELECT COUNT(*) as count FROM games').fetchone()
    if existing_games['count'] > 0:
        return
    
    current_time = int(time.time() * 1000)
    
    # Insert demo game
    cursor = db.execute(
        'INSERT INTO games (name, created_at) VALUES (?, ?)',
        ('Demo Game', current_time)
    )
    game_id = cursor.lastrowid
    
    # Insert 3 rounds
    rounds_data = [
        ('Round 1', 1),
        ('Round 2', 2),
        ('Round 3', 3)
    ]
    
    round_ids = []
    for round_name, order_index in rounds_data:
        cursor = db.execute(
            'INSERT INTO rounds (game_id, name, order_index) VALUES (?, ?, ?)',
            (game_id, round_name, order_index)
        )
        round_ids.append(cursor.lastrowid)
    
    # Insert 2 teams
    teams_data = [
        ('Team A', 'TEAM_A'),
        ('Team B', 'TEAM_B')
    ]
    
    team_ids = []
    for team_name, team_code in teams_data:
        cursor = db.execute(
            'INSERT INTO teams (game_id, name, code) VALUES (?, ?, ?)',
            (game_id, team_name, team_code)
        )
        team_ids.append(cursor.lastrowid)
    
    # Insert sample MCQ
    cursor = db.execute(
        '''INSERT INTO questions (game_id, text, opt_a, opt_b, opt_c, opt_d, correct_index, type) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (game_id, 'What is the capital of France?', 'London', 'Berlin', 'Paris', 'Madrid', 2, 'MCQ')
    )
    question_id = cursor.lastrowid
    
    # Initialize settings
    db.execute(
        '''INSERT INTO settings (game_id, current_round_id, current_question_id, state, deadline_epoch_ms, active_team_id)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (game_id, round_ids[0], question_id, 'IDLE', 0, None)
    )
    
    db.commit()
    click.echo('Database seeded with demo data')

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables"""
    init_db()
    click.echo('Initialized the database.')

@click.command('seed-db')
@with_appcontext
def seed_db_command():
    """Seed database with demo data"""
    seed_if_empty()

def init_app(app):
    """Register database functions with Flask app"""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)
import os
from pathlib import Path

class Config:
    """Configuration class with environment variable overrides and defaults"""
    
    # Flask core settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', '').lower() in ['true', '1', 'yes']
    TESTING = False
    
    # Directory paths
    BASE_DIR = Path(__file__).parent.parent
    INSTANCE_DIR = BASE_DIR / 'instance'
    
    # Database configuration
    DB_PATH = INSTANCE_DIR / 'app.db'
    
    # JSON configuration
    JSON_SORT_KEYS = False
    
    # Session cookie settings
    SESSION_COOKIE_SECURE = not DEBUG
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Socket.IO configuration
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"  # For development
    SOCKETIO_ASYNC_MODE = os.environ.get('SOCKETIO_ASYNC_MODE', 'eventlet')
    
    # Game settings
    DEFAULT_QUESTION_TIME_S = 30

def load_config():
    """Load and return configuration object"""
    return Config()
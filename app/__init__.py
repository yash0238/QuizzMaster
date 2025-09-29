import os
from flask import Flask, redirect, url_for
from flask_socketio import SocketIO
from pathlib import Path

from .config import load_config
from . import db

# Initialize Socket.IO at module level
socketio = SocketIO()

def create_app():
    """Flask application factory"""
    # Create Flask app with instance config
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
        static_folder="../static"
    )
    
    # Load configuration
    config = load_config()
    app.config.from_object(config)
    
    # Ensure instance directory exists
    instance_path = Path(app.instance_path)
    instance_path.mkdir(exist_ok=True)
    
    # Initialize database
    db.init_app(app)
    
    # Initialize Socket.IO with app
    socketio.init_app(
        app,
        cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'],
        async_mode=app.config['SOCKETIO_ASYNC_MODE']
    )
    
    # Store socketio in app extensions for access
    app.extensions['socketio'] = socketio
    
    # Register blueprints
    from .host import routes as host_routes
    from .team import routes as team_routes
    from .admin import routes as admin_routes
    
    app.register_blueprint(host_routes.bp, url_prefix='/host')
    app.register_blueprint(team_routes.bp, url_prefix='/team')
    app.register_blueprint(admin_routes.bp, url_prefix='/admin')
    
    # Root route redirects to host
    @app.route('/')
    def index():
        return redirect(url_for('host.index'))
    
    # Import socket handlers after app setup to register events
    from . import sockets
    
    return app
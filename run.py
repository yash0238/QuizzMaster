import os
from app import create_app, socketio

if __name__ == '__main__':
    # Create Flask app
    app = create_app()
    
    # Get host and port from environment
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get('PORT', '5000'))
    
    # Run with Socket.IO support
    socketio.run(
        app,
        host=host,
        port=port,
        allow_unsafe_werkzeug=True,
        use_reloader=False,
        log_output=True
    )

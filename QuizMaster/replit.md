# Overview

This is a real-time quiz application built with Flask and Flask-SocketIO that enables interactive quiz sessions between a host, multiple teams, and an admin. The application features live buzzing, answer selection, lifelines, and real-time state synchronization across all connected clients. Teams compete by buzzing in first and selecting answers, while the host displays questions and manages game flow, and the admin controls game state and rounds.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Flask Application Factory Pattern**: Uses `create_app()` function to initialize the Flask application with modular configuration
- **Blueprint-based Routing**: Organized into three main blueprints:
  - `/host` - Host interface for displaying questions and game state
  - `/team` - Team interface for buzzing and answering questions
  - `/admin` - Administrative interface for game management
- **Socket.IO Integration**: Real-time communication using Flask-SocketIO with eventlet async mode
- **Room-based Communication**: Uses Socket.IO rooms for targeted messaging:
  - Game rooms (`game:{id}`) for broadcasts to all participants
  - Team rooms (`game:{id}:team:{code}`) for team-specific messages

## Frontend Architecture
- **Server-side Rendered Templates**: Jinja2 templates with base template inheritance
- **Client-side Socket.IO**: JavaScript clients connect to Socket.IO for real-time updates
- **State Management**: Client-side state synchronized through Socket.IO events
- **Responsive CSS**: Grid-based layouts with modern CSS features

## Data Storage
- **SQLite Database**: File-based database stored in `instance/` directory
- **Schema Management**: SQL schema files in `migrations/` directory
- **Connection Management**: Per-request database connections with proper cleanup
- **Foreign Key Enforcement**: PRAGMA foreign_keys=ON enabled for referential integrity

## Real-time Communication
- **Event-driven Architecture**: Socket.IO events for state updates, buzzing, and room management
- **Room Management**: Automatic joining/leaving of game and team rooms
- **State Broadcasting**: Centralized state updates pushed to all relevant clients
- **Connection Handling**: Robust connection management with fallback transports

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web framework for HTTP routing and request handling
- **Flask-SocketIO**: WebSocket integration for real-time communication
- **eventlet**: WSGI server with async support for Socket.IO

## Client-side Dependencies
- **Socket.IO Client**: CDN-hosted Socket.IO client library (v4.7.5) for browser WebSocket connections

## Database
- **SQLite**: Embedded database engine (Python built-in, no external service required)
- **No ORM**: Direct SQL queries using Python's sqlite3 module

## Infrastructure
- **Replit Environment**: Configured to run on host 0.0.0.0 with PORT environment variable
- **Static File Serving**: Flask's built-in static file serving for CSS/JS assets
- **Template Rendering**: Jinja2 template engine (Flask built-in)
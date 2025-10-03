# Real‑Time Quiz Buzzer (Flask + Socket.IO)

A real‑time, KBC‑style quiz platform with host, team, and admin roles, live buzzing, countdown timer, and lifelines (50‑50) with synchronized state across clients.

## Features
- Real‑time buzzing with single‑winner lock per question and active team highlight.
- Lifelines: 50‑50 with per‑round usage tracking and deterministic masking per team.
- Host screen with question, options, timer, and active team banner.
- Team screen with buzzer, options, and lifelines (50‑50 server‑backed; phone/discussion local).
- Admin console to manage rounds, questions, timers, teams, and state transitions.

## Tech Stack
- Backend: Flask, Flask‑SocketIO, eventlet
- Frontend: Jinja templates, Socket.IO client, vanilla JS
- Database: SQLite (sqlite3, no ORM)

## Project Structure

# Real‑Time Quiz Buzzer (Flask + Socket.IO)

Fast, TV‑style quiz platform with host, team, and admin interfaces, live buzzing, lifelines, and synchronized state across clients.

## Features
- Real‑time state sync with Socket.IO rooms per game and per team.
- First‑buzz wins with strict locking and a single accepted buzz per question.
- Lifelines: 50‑50 (server‑enforced, per‑round), plus local Phone‑a‑Friend and Team Discussion.
- Host screen: live timer, active team banner, question and options.
- Admin console: set rounds/questions/state, start/add time, unlock buzzing, clear lifeline masks, and manage teams/questions.
- SQLite schema with foreign keys, WAL, and helpful indexes.

## Tech stack
- Backend: Flask, Flask‑SocketIO, eventlet
- Database: SQLite (sqlite3, raw SQL; no ORM)
- Frontend: Jinja templates, Socket.IO client, vanilla JS, responsive CSS

---


Open these routes in a browser:
- Host screen: http://localhost:5000/host
- Admin console: http://localhost:5000/admin
- Team lobby: http://localhost:5000/team/lobby
- Team page (by code): http://localhost:5000/team/<TEAM_CODE>

---

## Configuration

Environment variables (with defaults):
- SECRET_KEY: Flask secret (change in production)
- FLASK_DEBUG: true/false (relaxes cookie security if true)
- HOST: default 0.0.0.0
- PORT: default 5000
- SOCKETIO_ASYNC_MODE: default eventlet

Session/cookies:
- Secure, HttpOnly, SameSite=Lax by default; toggled by FLASK_DEBUG.

---

---

## How it works

- Rooms
  - game:{id}: everyone in the game (host, teams, admin)
  - game:{id}:team:{code}: team‑specific messages
- State
  - settings holds `state` in {IDLE, SHOW, LOCK, REVEAL}, `deadline_epoch_ms`, `current_round_id`, `current_question_id`, `active_team_id`
  - server broadcasts `state_update` whenever state changes
- Buzz flow
  - Teams emit `buzz` only in SHOW state
  - First successful insert wins and sets `active_team_id`; server emits `buzz_lock`
- Timer
  - Admin starts or adds time; clients render countdown from `deadline_epoch_ms`
- 50‑50 lifeline
  - One per team per round; deterministic masks saved to DB and re‑emitted on reconnect

---

## Admin actions (POST /admin/action)

Operations and fields:
- set_round: round_id
- set_question: question_id, seconds (default 30)
- set_state: state in {IDLE, SHOW, LOCK, REVEAL}
- start_timer: seconds
- add_time: seconds
- unlock_buzz: clears accepted buzz and active team for current question
- clear_masks: clears 50‑50 masks for current question
- set_active_team: team_id (0/blank to clear)
- add_team: name, code
- add_question: text, opt_a, opt_b, opt_c, opt_d, correct_index (0‑3), type (default MCQ)

---

## Database schema overview

- games: quiz instances
- rounds: ordered per game
- teams: per‑game unique code
- questions: text + four options + correct_index
- settings: singleton per game with state, deadline, current round/question, active team
- buzzer_events: tracks buzzes; partial unique constraint ensures only one accepted winner per question
- lifeline_usage: enforces per‑round 50‑50 usage
- team_masks: stores two masked options for 50‑50 per team/question

Initialize and seed:
flask --app app init-db
flask --app app seed-db


---

## Frontend notes

- base.html loads Socket.IO client and shared helpers
- host.js: state badge, countdown timer, options grid, active team banner
- team.js: buzzer states, option selection, 50‑50 application and local lifeline toggles
- styles.css: accessible focus, responsive layout, KBC‑themed components

---

## Development tips

- Keep Host, Admin, and two Team tabs open to validate locking and broadcasts.
- Use seed data to quickly test end‑to‑end flows (buzz, timer, 50‑50).
- For production: change SECRET_KEY, restrict CORS, consider external DB and a production‑grade WSGI/WebSocket stack.

---

## Contributing

- Fork, create a feature branch, commit with clear messages, open a PR.
- Keep UI changes accessible (focus states, contrast) and responsive.

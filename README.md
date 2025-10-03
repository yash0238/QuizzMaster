
Then open these routes in a browser:
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

-- SQLite database schema for quiz application
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS games (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rounds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  order_index INTEGER NOT NULL,
  FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
  UNIQUE(game_id, order_index)
);

CREATE TABLE IF NOT EXISTS teams (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  code TEXT NOT NULL,
  FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
  UNIQUE(game_id, code)
);

CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id INTEGER NOT NULL,
  text TEXT NOT NULL,
  opt_a TEXT NOT NULL,
  opt_b TEXT NOT NULL,
  opt_c TEXT NOT NULL,
  opt_d TEXT NOT NULL,
  correct_index INTEGER NOT NULL CHECK (correct_index BETWEEN 0 AND 3),
  type TEXT NOT NULL DEFAULT 'MCQ',
  FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
  game_id INTEGER PRIMARY KEY,
  current_round_id INTEGER,
  current_question_id INTEGER,
  state TEXT NOT NULL DEFAULT 'IDLE' CHECK (state IN ('IDLE','SHOW','LOCK','REVEAL')),
  deadline_epoch_ms INTEGER NOT NULL DEFAULT 0,
  active_team_id INTEGER,
  FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY (current_round_id) REFERENCES rounds(id) ON DELETE SET NULL,
  FOREIGN KEY (current_question_id) REFERENCES questions(id) ON DELETE SET NULL,
  FOREIGN KEY (active_team_id) REFERENCES teams(id) ON DELETE SET NULL
);

-- Lifelines: once per team per round
CREATE TABLE IF NOT EXISTS lifeline_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id INTEGER NOT NULL,
  team_id INTEGER NOT NULL,
  lifeline TEXT NOT NULL CHECK (lifeline IN ('FIFTY_FIFTY','PHONE','DISCUSSION')),
  used_in_round_id INTEGER NOT NULL,
  used_at INTEGER NOT NULL,
  FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
  FOREIGN KEY (used_in_round_id) REFERENCES rounds(id) ON DELETE CASCADE,
  UNIQUE(game_id, team_id, lifeline, used_in_round_id)
);

CREATE TABLE IF NOT EXISTS buzzer_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id INTEGER NOT NULL,
  team_id INTEGER NOT NULL,
  question_id INTEGER NOT NULL,
  ts INTEGER NOT NULL,
  accepted INTEGER NOT NULL DEFAULT 0 CHECK (accepted IN (0,1)),
  FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
  FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_buzzer_accepted_unique
ON buzzer_events(game_id, question_id) WHERE accepted = 1;

CREATE TABLE IF NOT EXISTS team_masks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id INTEGER NOT NULL,
  team_id INTEGER NOT NULL,
  question_id INTEGER NOT NULL,
  masked_i1 INTEGER NOT NULL CHECK (masked_i1 BETWEEN 0 AND 3),
  masked_i2 INTEGER NOT NULL CHECK (masked_i2 BETWEEN 0 AND 3),
  ts INTEGER NOT NULL,
  FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
  FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
  UNIQUE(game_id, team_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_rounds_game_order ON rounds(game_id, order_index);
CREATE INDEX IF NOT EXISTS idx_teams_game_code ON teams(game_id, code);
CREATE INDEX IF NOT EXISTS idx_questions_game ON questions(game_id);
CREATE INDEX IF NOT EXISTS idx_buzzer_events_game_question ON buzzer_events(game_id, question_id);
CREATE INDEX IF NOT EXISTS idx_buzzer_events_accepted ON buzzer_events(game_id, question_id, accepted);
CREATE INDEX IF NOT EXISTS idx_team_masks_lookup ON team_masks(game_id, team_id, question_id);
CREATE INDEX IF NOT EXISTS idx_lifeline_usage_lookup ON lifeline_usage(game_id, team_id, lifeline, used_in_round_id);

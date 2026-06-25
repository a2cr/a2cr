from __future__ import annotations

import sqlite3


SCHEMA_VERSION = 2


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_key TEXT NOT NULL UNIQUE,
  display_name TEXT,
  root_path TEXT,
  git_remote TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_name TEXT,
  agent_label TEXT,
  model_source TEXT,
  session_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workbatons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  actor_id INTEGER REFERENCES actors(id) ON DELETE SET NULL,
  slot_name TEXT NOT NULL UNIQUE,
  slot_number INTEGER UNIQUE,
  content_json TEXT NOT NULL,
  content_text TEXT NOT NULL,
  original_length INTEGER,
  compressed_tokens INTEGER,
  model_source TEXT,
  pinned INTEGER NOT NULL DEFAULT 0,
  stale INTEGER NOT NULL DEFAULT 0,
  archived INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workstash_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  actor_id INTEGER REFERENCES actors(id) ON DELETE SET NULL,
  entry_key TEXT NOT NULL UNIQUE,
  value TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workthreads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  actor_id INTEGER REFERENCES actors(id) ON DELETE SET NULL,
  thread_key TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workthread_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  thread_id INTEGER NOT NULL REFERENCES workthreads(id) ON DELETE CASCADE,
  actor_id INTEGER REFERENCES actors(id) ON DELETE SET NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workthread_participants (
  thread_id INTEGER NOT NULL REFERENCES workthreads(id) ON DELETE CASCADE,
  actor_id INTEGER NOT NULL REFERENCES actors(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'participant',
  joined_at TEXT NOT NULL,
  PRIMARY KEY(thread_id, actor_id)
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
  actor_id INTEGER REFERENCES actors(id) ON DELETE SET NULL,
  object_type TEXT NOT NULL,
  object_key TEXT,
  action TEXT NOT NULL,
  summary TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS object_references (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL,
  source_key TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_key TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workbatons_project_updated
  ON workbatons(project_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_workstash_project_updated
  ON workstash_entries(project_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_workthreads_project_updated
  ON workthreads(project_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_workthread_messages_thread_created
  ON workthread_messages(thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_workthread_participants_actor
  ON workthread_participants(actor_id);
CREATE INDEX IF NOT EXISTS idx_events_project_created
  ON events(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_references_source
  ON object_references(source_type, source_key);
CREATE INDEX IF NOT EXISTS idx_references_target
  ON object_references(target_type, target_key);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)

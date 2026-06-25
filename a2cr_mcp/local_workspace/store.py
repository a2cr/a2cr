from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import local_db_path
from .db import connect


_WORKSTASH_REF = re.compile(r"\bWorkStash:\s*([A-Za-z0-9_.:-]{1,256})")
_WORKTHREAD_REF = re.compile(r"\bWorkThread:\s*([A-Za-z0-9_.:-]{1,256})")
_WORKBATON_REF = re.compile(r"\bWorkBaton:\s*([A-Za-z0-9_.:-]{1,256})")
_HANDLE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,256}$")
_MESSAGE_SNIPPET_CHARS = 1200


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _content_text(content: dict[str, Any]) -> str:
    parts: list[str] = []
    for value in content.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, dict):
            parts.append(_json(value))
        else:
            parts.append(str(value))
    return "\n".join(parts)


def _project_key_from_slot(slot_name: str | None, project: str | None = None) -> str:
    if project and project.strip():
        return project.strip()
    if slot_name and "-" in slot_name:
        return slot_name.split("-", 1)[0].strip() or "default"
    if slot_name and slot_name.strip():
        return slot_name.strip()
    return "default"


def _project_key_from_env(project: str | None = None) -> str:
    if project and project.strip():
        return project.strip()
    env_project = os.environ.get("A2CR_PROJECT")
    if env_project and env_project.strip():
        return env_project.strip()
    root = os.environ.get("A2CR_PROJECT_ROOT")
    if root and root.strip():
        return Path(root).expanduser().resolve().name or root.strip()
    return Path.cwd().name or "default"


def _row_to_dict(row) -> dict[str, Any]:
    return dict(row)


def _validate_handle(value: str, label: str) -> dict[str, Any] | None:
    if isinstance(value, str) and _HANDLE_RE.fullmatch(value):
        return None
    return {
        "status": "validation_error",
        "message": f"{label} must be 1-256 characters and contain only letters, digits, underscore, dot, colon, or hyphen.",
    }


def _trim_message_body(body: str) -> dict[str, Any]:
    if len(body) <= _MESSAGE_SNIPPET_CHARS:
        return {"body": body, "truncated": False}
    return {
        "body": body[:_MESSAGE_SNIPPET_CHARS].rstrip(),
        "truncated": True,
        "original_length": len(body),
    }


def _reference_keys(pattern: re.Pattern[str], text: str) -> list[str]:
    return sorted({match.rstrip(".,;:)") for match in pattern.findall(text) if match.rstrip(".,;:)")})


class LocalWorkspaceStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or local_db_path()

    def account_limits(self) -> dict[str, Any]:
        return {
            "storage_mode": "local",
            "requires_api_key": False,
            "hard_slot_limit": None,
            "retention_policy": "none_by_default",
            "workstash_storage_limit": None,
            "database_path": str(self.db_path),
        }

    def dashboard(self) -> dict[str, Any]:
        with connect(self.db_path) as conn:
            counts = {
                "projects": conn.execute("SELECT COUNT(*) AS count FROM projects").fetchone()["count"],
                "workbatons": conn.execute("SELECT COUNT(*) AS count FROM workbatons WHERE archived = 0").fetchone()["count"],
                "workstash_entries": conn.execute("SELECT COUNT(*) AS count FROM workstash_entries").fetchone()["count"],
                "workthreads": conn.execute("SELECT COUNT(*) AS count FROM workthreads WHERE state != 'archived'").fetchone()["count"],
                "events": conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()["count"],
            }
            projects = conn.execute(
                """
                SELECT p.project_key, p.display_name, p.updated_at,
                       COUNT(DISTINCT wb.id) AS workbaton_count,
                       COUNT(DISTINCT ws.id) AS workstash_count,
                       COUNT(DISTINCT wt.id) AS workthread_count
                FROM projects p
                LEFT JOIN workbatons wb ON wb.project_id = p.id AND wb.archived = 0
                LEFT JOIN workstash_entries ws ON ws.project_id = p.id
                LEFT JOIN workthreads wt ON wt.project_id = p.id AND wt.state != 'archived'
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                LIMIT 20
                """
            ).fetchall()
            recent_events = self._event_rows(conn, limit=12)
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "status": "ok",
            "storage_mode": "local",
            "database_path": str(self.db_path),
            "database_size_bytes": db_size,
            "counts": counts,
            "projects": [_row_to_dict(row) for row in projects],
            "recent_events": recent_events,
        }

    def list_workbatons(self, *, include_archived: bool = False, limit: int = 100) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        where = "" if include_archived else "WHERE wb.archived = 0"
        with connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT wb.slot_name, wb.slot_number, wb.compressed_tokens,
                       wb.model_source, wb.pinned, wb.stale, wb.archived,
                       wb.created_at, wb.updated_at, p.project_key,
                       a.client_name, a.agent_label, a.session_id
                FROM workbatons wb
                JOIN projects p ON p.id = wb.project_id
                LEFT JOIN actors a ON a.id = wb.actor_id
                {where}
                ORDER BY wb.pinned DESC, wb.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return {
            "status": "ok",
            "storage_mode": "local",
            "items": [self._boolean_baton_fields(_row_to_dict(row)) for row in rows],
            "item_count": len(rows),
        }

    def get_workbaton(self, slot_name: str) -> dict[str, Any]:
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT wb.slot_name, wb.slot_number, wb.content_json, wb.content_text,
                       wb.original_length, wb.compressed_tokens, wb.model_source,
                       wb.pinned, wb.stale, wb.archived, wb.created_at, wb.updated_at,
                       p.project_key, a.client_name, a.agent_label, a.session_id
                FROM workbatons wb
                JOIN projects p ON p.id = wb.project_id
                LEFT JOIN actors a ON a.id = wb.actor_id
                WHERE wb.slot_name = ?
                """,
                (slot_name,),
            ).fetchone()
            if row is None:
                return {"status": "not_found", "storage_mode": "local", "slot_name": slot_name}
            references = self._references(conn, "WorkBaton", slot_name)
            referenced_by = self._referenced_by(conn, "WorkBaton", slot_name)
        item = self._boolean_baton_fields(_row_to_dict(row))
        return {
            "status": "loaded",
            "storage_mode": "local",
            **item,
            "content": json.loads(row["content_json"]),
            "content_text": row["content_text"],
            "references": references,
            "referenced_by": referenced_by,
        }

    def update_workbaton_state(self, slot_name: str, action: str) -> dict[str, Any]:
        actions = {
            "pin": ("pinned", 1, "pinned"),
            "unpin": ("pinned", 0, "unpinned"),
            "stale": ("stale", 1, "stale"),
            "unstale": ("stale", 0, "fresh"),
            "archive": ("archived", 1, "archived"),
            "unarchive": ("archived", 0, "active"),
        }
        if action == "delete":
            return self.delete_context(slot_name)
        if action not in actions:
            return {"status": "validation_error", "storage_mode": "local", "message": "unsupported WorkBaton action"}
        column, value, status = actions[action]
        now = _now()
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT project_id, actor_id FROM workbatons WHERE slot_name = ?",
                (slot_name,),
            ).fetchone()
            if row is None:
                return {"status": "not_found", "storage_mode": "local", "slot_name": slot_name}
            conn.execute(
                f"UPDATE workbatons SET {column} = ?, updated_at = ? WHERE slot_name = ?",
                (value, now, slot_name),
            )
            self._record_event(conn, row["project_id"], row["actor_id"], "WorkBaton", slot_name, action, now)
        return {
            "status": status,
            "storage_mode": "local",
            "slot_name": slot_name,
            "updated_at": now,
        }

    def save_context(
        self,
        *,
        slot_name: str,
        content: dict[str, Any],
        original_length: int | None,
        compressed_tokens: int,
        model_source: str | None,
        slot_number: int | None,
    ) -> dict[str, Any]:
        now = _now()
        project_key = _project_key_from_slot(slot_name)
        content_json = _json(content)
        content_text = _content_text(content)
        with connect(self.db_path) as conn:
            project_id = self._project_id(conn, project_key, now)
            actor_id = self._actor_id(conn, model_source=model_source, now=now)
            if slot_number is not None:
                conn.execute(
                    "DELETE FROM workbatons WHERE slot_number = ? AND slot_name != ?",
                    (slot_number, slot_name),
                )
            conn.execute(
                """
                INSERT INTO workbatons(
                  project_id, actor_id, slot_name, slot_number, content_json,
                  content_text, original_length, compressed_tokens, model_source,
                  created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slot_name) DO UPDATE SET
                  project_id = excluded.project_id,
                  actor_id = excluded.actor_id,
                  slot_number = excluded.slot_number,
                  content_json = excluded.content_json,
                  content_text = excluded.content_text,
                  original_length = excluded.original_length,
                  compressed_tokens = excluded.compressed_tokens,
                  model_source = excluded.model_source,
                  archived = 0,
                  stale = 0,
                  updated_at = excluded.updated_at
                """,
                (
                    project_id,
                    actor_id,
                    slot_name,
                    slot_number,
                    content_json,
                    content_text,
                    original_length,
                    compressed_tokens,
                    model_source,
                    now,
                    now,
                ),
            )
            self._replace_references(conn, "WorkBaton", slot_name, content, now)
            self._record_event(conn, project_id, actor_id, "WorkBaton", slot_name, "save", now)
        return {
            "status": "saved",
            "storage_mode": "local",
            "slot_name": slot_name,
            "slot_number": slot_number,
            "compressed_tokens": compressed_tokens,
            "updated_at": now,
        }

    def list_contexts(self) -> list[dict[str, Any]]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT slot_name, slot_number, compressed_tokens, model_source,
                       pinned, stale, archived, created_at, updated_at
                FROM workbatons
                WHERE archived = 0
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [
            {
                **_row_to_dict(row),
                "storage_mode": "local",
                "pinned": bool(row["pinned"]),
                "stale": bool(row["stale"]),
                "archived": bool(row["archived"]),
            }
            for row in rows
        ]

    def load_context(
        self,
        *,
        slot_name: str | None = None,
        slot_number: int | None = None,
    ) -> dict[str, Any]:
        if slot_number is None and not slot_name:
            return {"status": "validation_error", "message": "slot_number or slot_name is required"}
        where = "slot_number = ?" if slot_number is not None else "slot_name = ?"
        value = slot_number if slot_number is not None else slot_name
        with connect(self.db_path) as conn:
            row = conn.execute(
                f"""
                SELECT slot_name, slot_number, content_json, compressed_tokens,
                       model_source, pinned, stale, archived, created_at, updated_at
                FROM workbatons
                WHERE {where}
                """,
                (value,),
            ).fetchone()
        if row is None:
            return {"status": "not_found", "slot_name": slot_name, "slot_number": slot_number}
        content = json.loads(row["content_json"])
        return {
            "status": "loaded",
            "storage_mode": "local",
            "slot_name": row["slot_name"],
            "slot_number": row["slot_number"],
            "content": content,
            "compressed_tokens": row["compressed_tokens"],
            "model_source": row["model_source"],
            "pinned": bool(row["pinned"]),
            "stale": bool(row["stale"]),
            "archived": bool(row["archived"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def resume_context(
        self,
        *,
        slot_name: str | None = None,
        slot_number: int | None = None,
        project: str | None = None,
        prefer_latest: bool = False,
    ) -> dict[str, Any]:
        if slot_number is not None or slot_name:
            return self.load_context(slot_name=slot_name, slot_number=slot_number)
        candidates = self.list_contexts()
        if project:
            prefix = f"{project}-"
            candidates = [
                item
                for item in candidates
                if item["slot_name"] == project or str(item["slot_name"]).startswith(prefix)
            ]
        candidates = [
            item for item in candidates
            if not item.get("stale") and not item.get("archived")
        ]
        if not candidates:
            return {"status": "not_found" if project else "no_active_context", "storage_mode": "local"}
        if len(candidates) == 1 or prefer_latest:
            return self.load_context(slot_name=candidates[0]["slot_name"])
        return {"status": "candidates", "storage_mode": "local", "candidates": candidates}

    def delete_context(self, slot_name: str) -> dict[str, Any]:
        now = _now()
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT project_id, actor_id FROM workbatons WHERE slot_name = ?",
                (slot_name,),
            ).fetchone()
            if row is None:
                return {"status": "not_found", "storage_mode": "local", "slot_name": slot_name}
            conn.execute("DELETE FROM workbatons WHERE slot_name = ?", (slot_name,))
            conn.execute(
                "DELETE FROM object_references WHERE source_type = 'WorkBaton' AND source_key = ?",
                (slot_name,),
            )
            self._record_event(conn, row["project_id"], row["actor_id"], "WorkBaton", slot_name, "delete", now)
        return {"status": "deleted", "storage_mode": "local", "slot_name": slot_name}

    def store_work_stash(
        self,
        *,
        entry_key: str,
        value: str,
        tags: list[str] | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        tags = tags or []
        project_key = _project_key_from_env(project)
        size_bytes = len(value.encode("utf-8"))
        with connect(self.db_path) as conn:
            project_id = self._project_id(conn, project_key, now)
            actor_id = self._actor_id(conn, model_source=None, now=now)
            conn.execute(
                """
                INSERT INTO workstash_entries(
                  project_id, actor_id, entry_key, value, tags_json, size_bytes,
                  created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entry_key) DO UPDATE SET
                  project_id = excluded.project_id,
                  actor_id = excluded.actor_id,
                  value = excluded.value,
                  tags_json = excluded.tags_json,
                  size_bytes = excluded.size_bytes,
                  updated_at = excluded.updated_at
                """,
                (project_id, actor_id, entry_key, value, _json(tags), size_bytes, now, now),
            )
            self._record_event(conn, project_id, actor_id, "WorkStash", entry_key, "store", now)
        return {
            "status": "stored",
            "storage_mode": "local",
            "entry_key": entry_key,
            "size_bytes": size_bytes,
            "tags": tags,
            "project_key": project_key,
            "updated_at": now,
        }

    def get_work_stash(self, entry_key: str) -> dict[str, Any]:
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT ws.entry_key, ws.value, ws.tags_json, ws.size_bytes,
                       ws.created_at, ws.updated_at, p.project_key,
                       a.client_name, a.agent_label, a.session_id
                FROM workstash_entries ws
                JOIN projects p ON p.id = ws.project_id
                LEFT JOIN actors a ON a.id = ws.actor_id
                WHERE ws.entry_key = ?
                """,
                (entry_key,),
            ).fetchone()
            referenced_by = self._referenced_by(conn, "WorkStash", entry_key)
        if row is None:
            return {"status": "not_found", "storage_mode": "local", "entry_key": entry_key}
        return {
            "status": "loaded",
            "storage_mode": "local",
            "entry_key": row["entry_key"],
            "value": row["value"],
            "tags": json.loads(row["tags_json"]),
            "size_bytes": row["size_bytes"],
            "project_key": row["project_key"],
            "client_name": row["client_name"],
            "agent_label": row["agent_label"],
            "session_id": row["session_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "referenced_by": referenced_by,
        }

    def list_work_stash(self, tag_filter: str | None = None) -> dict[str, Any]:
        query = """
            SELECT ws.entry_key, ws.tags_json, ws.size_bytes, ws.created_at, ws.updated_at,
                   p.project_key, a.client_name, a.agent_label, a.session_id
            FROM workstash_entries ws
            JOIN projects p ON p.id = ws.project_id
            LEFT JOIN actors a ON a.id = ws.actor_id
            ORDER BY ws.updated_at DESC
        """
        with connect(self.db_path) as conn:
            rows = conn.execute(query).fetchall()
        entries = []
        for row in rows:
            tags = json.loads(row["tags_json"])
            if tag_filter and tag_filter not in tags:
                continue
            entries.append({
                "entry_key": row["entry_key"],
                "tags": tags,
                "size_bytes": row["size_bytes"],
                "project_key": row["project_key"],
                "client_name": row["client_name"],
                "agent_label": row["agent_label"],
                "session_id": row["session_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        return {
            "status": "ok",
            "storage_mode": "local",
            "entries": entries,
            "entry_count": len(entries),
            "total_size_bytes": sum(item["size_bytes"] for item in entries),
            "quota_bytes": None,
            "entry_limit": None,
            "cleanup_hint": "Delete WorkStash entries that are no longer referenced or useful.",
        }

    def delete_work_stash(self, entry_key: str) -> dict[str, Any]:
        now = _now()
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT project_id, actor_id FROM workstash_entries WHERE entry_key = ?",
                (entry_key,),
            ).fetchone()
            if row is None:
                return {"status": "not_found", "storage_mode": "local", "entry_key": entry_key}
            conn.execute("DELETE FROM workstash_entries WHERE entry_key = ?", (entry_key,))
            self._record_event(conn, row["project_id"], row["actor_id"], "WorkStash", entry_key, "delete", now)
        return {"status": "deleted", "storage_mode": "local", "entry_key": entry_key}

    def list_actors(self, limit: int = 100) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT a.id, a.client_name, a.agent_label, a.model_source, a.session_id,
                       a.created_at, a.updated_at,
                       COUNT(DISTINCT wb.id) AS workbaton_count,
                       COUNT(DISTINCT ws.id) AS workstash_count,
                       COUNT(DISTINCT wtm.id) AS workthread_message_count
                FROM actors a
                LEFT JOIN workbatons wb ON wb.actor_id = a.id
                LEFT JOIN workstash_entries ws ON ws.actor_id = a.id
                LEFT JOIN workthread_messages wtm ON wtm.actor_id = a.id
                GROUP BY a.id
                ORDER BY a.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return {
            "status": "ok",
            "storage_mode": "local",
            "actors": [_row_to_dict(row) for row in rows],
            "actor_count": len(rows),
        }

    def list_events(self, limit: int = 100) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        with connect(self.db_path) as conn:
            rows = self._event_rows(conn, limit=limit)
        return {
            "status": "ok",
            "storage_mode": "local",
            "events": rows,
            "event_count": len(rows),
        }

    def export_workspace(self) -> dict[str, Any]:
        with connect(self.db_path) as conn:
            batons = conn.execute("SELECT * FROM workbatons ORDER BY updated_at DESC").fetchall()
            stash = conn.execute("SELECT * FROM workstash_entries ORDER BY updated_at DESC").fetchall()
            threads = conn.execute("SELECT * FROM workthreads ORDER BY updated_at DESC").fetchall()
            messages = conn.execute("SELECT * FROM workthread_messages ORDER BY created_at ASC").fetchall()
            participants = conn.execute("SELECT * FROM workthread_participants ORDER BY joined_at ASC").fetchall()
            references = conn.execute("SELECT * FROM object_references ORDER BY created_at ASC").fetchall()
            events = conn.execute("SELECT * FROM events ORDER BY created_at ASC").fetchall()
            projects = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
            actors = conn.execute("SELECT * FROM actors ORDER BY updated_at DESC").fetchall()
        return {
            "status": "ok",
            "storage_mode": "local",
            "exported_at": _now(),
            "database_path": str(self.db_path),
            "projects": [_row_to_dict(row) for row in projects],
            "actors": [_row_to_dict(row) for row in actors],
            "workbatons": [_row_to_dict(row) for row in batons],
            "workstash_entries": [_row_to_dict(row) for row in stash],
            "workthreads": [_row_to_dict(row) for row in threads],
            "workthread_messages": [_row_to_dict(row) for row in messages],
            "workthread_participants": [_row_to_dict(row) for row in participants],
            "object_references": [_row_to_dict(row) for row in references],
            "events": [_row_to_dict(row) for row in events],
        }

    def backup_database(self, backup_dir: Path | None = None) -> dict[str, Any]:
        target_dir = backup_dir or self.db_path.parent / "backups"
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        target = target_dir / f"a2cr-{stamp}.db"
        suffix = 1
        while target.exists():
            target = target_dir / f"a2cr-{stamp}-{suffix}.db"
            suffix += 1
        with connect(self.db_path) as source, sqlite3.connect(target) as destination:
            source.backup(destination)
        return {
            "status": "backed_up",
            "storage_mode": "local",
            "source_path": str(self.db_path),
            "backup_path": str(target),
            "size_bytes": target.stat().st_size,
        }

    def create_work_thread(
        self,
        *,
        thread_key: str,
        title: str,
        initial_message: str | None = None,
        project: str | None = None,
        participant_label: str | None = None,
        model_source: str | None = None,
    ) -> dict[str, Any]:
        validation_error = _validate_handle(thread_key, "thread_key")
        if validation_error:
            return {**validation_error, "storage_mode": "local", "thread_key": thread_key}
        clean_title = (title or "").strip()
        if not clean_title:
            return {"status": "validation_error", "storage_mode": "local", "message": "title is required"}
        now = _now()
        project_key = _project_key_from_slot(None, project or os.environ.get("A2CR_PROJECT_ROOT"))
        with connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT thread_key, state FROM workthreads WHERE thread_key = ?",
                (thread_key,),
            ).fetchone()
            if existing:
                return {
                    "status": "exists",
                    "storage_mode": "local",
                    "thread_key": existing["thread_key"],
                    "state": existing["state"],
                    "message": "WorkThread already exists.",
                }
            project_id = self._project_id(conn, project_key, now)
            actor_id = self._actor_id(
                conn,
                model_source=model_source,
                agent_label=participant_label,
                now=now,
            )
            conn.execute(
                """
                INSERT INTO workthreads(project_id, actor_id, thread_key, title, state, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'open', ?, ?)
                """,
                (project_id, actor_id, thread_key, clean_title, now, now),
            )
            thread_id = int(conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
            self._join_work_thread(conn, thread_id, actor_id, "creator", now)
            message_count = 0
            if initial_message:
                self._insert_work_thread_message(
                    conn,
                    thread_id=thread_id,
                    actor_id=actor_id,
                    body=initial_message,
                    now=now,
                )
                message_count = 1
            self._replace_work_thread_references(conn, thread_id, thread_key, now)
            self._record_event(conn, project_id, actor_id, "WorkThread", thread_key, "create", now)
        return {
            "status": "created",
            "storage_mode": "local",
            "thread_key": thread_key,
            "title": clean_title,
            "state": "open",
            "message_count": message_count,
            "updated_at": now,
        }

    def post_work_thread_message(
        self,
        *,
        thread_key: str,
        body: str,
        participant_label: str | None = None,
        model_source: str | None = None,
    ) -> dict[str, Any]:
        validation_error = _validate_handle(thread_key, "thread_key")
        if validation_error:
            return {**validation_error, "storage_mode": "local", "thread_key": thread_key}
        clean_body = (body or "").strip()
        if not clean_body:
            return {"status": "validation_error", "storage_mode": "local", "message": "body is required"}
        now = _now()
        with connect(self.db_path) as conn:
            thread = self._thread_row(conn, thread_key)
            if thread is None:
                return {"status": "not_found", "storage_mode": "local", "thread_key": thread_key}
            if thread["state"] != "open":
                return {
                    "status": "thread_not_open",
                    "storage_mode": "local",
                    "thread_key": thread_key,
                    "state": thread["state"],
                }
            actor_id = self._actor_id(
                conn,
                model_source=model_source,
                agent_label=participant_label,
                now=now,
            )
            self._join_work_thread(conn, thread["id"], actor_id, "participant", now)
            message_id = self._insert_work_thread_message(
                conn,
                thread_id=thread["id"],
                actor_id=actor_id,
                body=clean_body,
                now=now,
            )
            conn.execute(
                "UPDATE workthreads SET updated_at = ? WHERE id = ?",
                (now, thread["id"]),
            )
            self._replace_work_thread_references(conn, thread["id"], thread_key, now)
            self._record_event(conn, thread["project_id"], actor_id, "WorkThread", thread_key, "post", now)
        return {
            "status": "posted",
            "storage_mode": "local",
            "thread_key": thread_key,
            "message_id": message_id,
            "updated_at": now,
        }

    def list_work_threads(
        self,
        *,
        state: str | None = None,
        include_archived: bool = False,
        limit: int = 20,
    ) -> dict[str, Any]:
        allowed_states = {None, "open", "closed", "archived"}
        if state not in allowed_states:
            return {"status": "validation_error", "storage_mode": "local", "message": "state must be open, closed, or archived"}
        limit = max(1, min(limit, 100))
        clauses = []
        params: list[Any] = []
        if state:
            clauses.append("wt.state = ?")
            params.append(state)
        elif not include_archived:
            clauses.append("wt.state != 'archived'")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT wt.thread_key, wt.title, wt.state, wt.created_at, wt.updated_at,
                       p.project_key,
                       COUNT(DISTINCT wtm.id) AS message_count,
                       COUNT(DISTINCT wtp.actor_id) AS participant_count,
                       MAX(wtm.created_at) AS last_message_at
                FROM workthreads wt
                JOIN projects p ON p.id = wt.project_id
                LEFT JOIN workthread_messages wtm ON wtm.thread_id = wt.id
                LEFT JOIN workthread_participants wtp ON wtp.thread_id = wt.id
                {where}
                GROUP BY wt.id
                ORDER BY wt.updated_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return {
            "status": "ok",
            "storage_mode": "local",
            "threads": [_row_to_dict(row) for row in rows],
            "thread_count": len(rows),
        }

    def get_work_thread(
        self,
        *,
        thread_key: str,
        include_messages: bool = True,
        message_limit: int = 20,
    ) -> dict[str, Any]:
        validation_error = _validate_handle(thread_key, "thread_key")
        if validation_error:
            return {**validation_error, "storage_mode": "local", "thread_key": thread_key}
        message_limit = max(1, min(message_limit, 100))
        with connect(self.db_path) as conn:
            thread = self._thread_row(conn, thread_key)
            if thread is None:
                return {"status": "not_found", "storage_mode": "local", "thread_key": thread_key}
            participants = self._work_thread_participants(conn, thread["id"])
            references = self._references(conn, "WorkThread", thread_key)
            messages: list[dict[str, Any]] = []
            total_messages = conn.execute(
                "SELECT COUNT(*) AS count FROM workthread_messages WHERE thread_id = ?",
                (thread["id"],),
            ).fetchone()["count"]
            if include_messages:
                rows = conn.execute(
                    """
                    SELECT wtm.id, wtm.body, wtm.created_at,
                           a.client_name, a.agent_label, a.model_source, a.session_id
                    FROM workthread_messages wtm
                    LEFT JOIN actors a ON a.id = wtm.actor_id
                    WHERE wtm.thread_id = ?
                    ORDER BY wtm.created_at DESC, wtm.id DESC
                    LIMIT ?
                    """,
                    (thread["id"], message_limit),
                ).fetchall()
                for row in reversed(rows):
                    body = _trim_message_body(row["body"])
                    messages.append({
                        "message_id": row["id"],
                        "created_at": row["created_at"],
                        "client_name": row["client_name"],
                        "agent_label": row["agent_label"],
                        "model_source": row["model_source"],
                        "session_id": row["session_id"],
                        **body,
                    })
        return {
            "status": "loaded",
            "storage_mode": "local",
            "thread_key": thread["thread_key"],
            "title": thread["title"],
            "state": thread["state"],
            "project_key": thread["project_key"],
            "created_at": thread["created_at"],
            "updated_at": thread["updated_at"],
            "participants": participants,
            "references": references,
            "message_count": total_messages,
            "messages_returned": len(messages),
            "messages_truncated_by_limit": include_messages and total_messages > len(messages),
            "messages": messages if include_messages else [],
            "response_policy": "MCP returns recent messages with long bodies truncated; use the future local UI for full conversation inspection.",
        }

    def close_work_thread(self, thread_key: str) -> dict[str, Any]:
        return self._set_work_thread_state(thread_key, "closed")

    def archive_work_thread(self, thread_key: str) -> dict[str, Any]:
        return self._set_work_thread_state(thread_key, "archived")

    def search_contexts(
        self,
        query: str = "",
        *,
        object_type: str | None = None,
        limit: int = 10,
        project: str | None = None,
        tag: str | None = None,
        state: str | None = None,
        agent: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        slot: str | None = None,
    ) -> dict[str, Any]:
        term = (query or "").strip()
        normalized_type = object_type.strip() if isinstance(object_type, str) else None
        if normalized_type == "event":
            normalized_type = "Event"
        allowed_types = {None, "WorkBaton", "WorkStash", "WorkThread", "Event"}
        if normalized_type not in allowed_types:
            return {"status": "validation_error", "message": "object_type must be WorkBaton, WorkStash, WorkThread, or Event.", "storage_mode": "local"}
        if state and state not in {"open", "closed", "archived"}:
            return {"status": "validation_error", "message": "state must be open, closed, or archived.", "storage_mode": "local"}
        limit = max(1, min(limit, 50))
        needle = f"%{term.lower()}%" if term else "%"
        project_needle = f"%{project.lower()}%" if project else None
        tag_needle = f"%{tag.lower()}%" if tag else None
        agent_needle = f"%{agent.lower()}%" if agent else None
        slot_needle = f"%{slot.lower()}%" if slot else None
        results: list[dict[str, Any]] = []
        with connect(self.db_path) as conn:
            if normalized_type in {None, "WorkBaton"} and not tag and not state:
                clauses = ["(lower(wb.slot_name) LIKE ? OR lower(wb.content_text) LIKE ?)"]
                params: list[Any] = [needle, needle]
                if project_needle:
                    clauses.append("lower(p.project_key) LIKE ?")
                    params.append(project_needle)
                if agent_needle:
                    clauses.append("(lower(COALESCE(a.client_name, '')) LIKE ? OR lower(COALESCE(a.agent_label, '')) LIKE ? OR lower(COALESCE(a.model_source, '')) LIKE ? OR lower(COALESCE(a.session_id, '')) LIKE ?)")
                    params.extend([agent_needle, agent_needle, agent_needle, agent_needle])
                if slot_needle:
                    clauses.append("(lower(wb.slot_name) LIKE ? OR CAST(wb.slot_number AS TEXT) LIKE ?)")
                    params.extend([slot_needle, slot_needle])
                if date_from:
                    clauses.append("wb.updated_at >= ?")
                    params.append(date_from)
                if date_to:
                    clauses.append("wb.updated_at <= ?")
                    params.append(date_to)
                rows = conn.execute(
                    f"""
                    SELECT wb.slot_name, wb.slot_number, wb.content_text, wb.updated_at,
                           p.project_key
                    FROM workbatons wb
                    JOIN projects p ON p.id = wb.project_id
                    LEFT JOIN actors a ON a.id = wb.actor_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY wb.updated_at DESC
                    LIMIT ?
                    """,
                    (*params, limit),
                ).fetchall()
                results.extend(
                    self._search_result("WorkBaton", row["slot_name"], row["content_text"], row["updated_at"], term, project_key=row["project_key"])
                    for row in rows
                )
            if normalized_type in {None, "WorkStash"} and not state and not slot:
                clauses = ["(lower(ws.entry_key) LIKE ? OR lower(ws.value) LIKE ? OR lower(ws.tags_json) LIKE ?)"]
                params = [needle, needle, needle]
                if project_needle:
                    clauses.append("lower(p.project_key) LIKE ?")
                    params.append(project_needle)
                if tag_needle:
                    clauses.append("lower(ws.tags_json) LIKE ?")
                    params.append(tag_needle)
                if agent_needle:
                    clauses.append("(lower(COALESCE(a.client_name, '')) LIKE ? OR lower(COALESCE(a.agent_label, '')) LIKE ? OR lower(COALESCE(a.model_source, '')) LIKE ? OR lower(COALESCE(a.session_id, '')) LIKE ?)")
                    params.extend([agent_needle, agent_needle, agent_needle, agent_needle])
                if date_from:
                    clauses.append("ws.updated_at >= ?")
                    params.append(date_from)
                if date_to:
                    clauses.append("ws.updated_at <= ?")
                    params.append(date_to)
                rows = conn.execute(
                    f"""
                    SELECT ws.entry_key, ws.value, ws.tags_json, ws.updated_at,
                           p.project_key
                    FROM workstash_entries ws
                    JOIN projects p ON p.id = ws.project_id
                    LEFT JOIN actors a ON a.id = ws.actor_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY ws.updated_at DESC
                    LIMIT ?
                    """,
                    (*params, limit),
                ).fetchall()
                results.extend(
                    self._search_result("WorkStash", row["entry_key"], row["value"], row["updated_at"], term, project_key=row["project_key"], tags=json.loads(row["tags_json"]))
                    for row in rows
                )
            if normalized_type in {None, "WorkThread"} and not tag and not slot:
                clauses = ["(lower(wt.thread_key) LIKE ? OR lower(wt.title) LIKE ? OR lower(COALESCE(wtm.body, '')) LIKE ?)"]
                params = [needle, needle, needle]
                if project_needle:
                    clauses.append("lower(p.project_key) LIKE ?")
                    params.append(project_needle)
                if state:
                    clauses.append("wt.state = ?")
                    params.append(state)
                if agent_needle:
                    clauses.append(
                        """
                        EXISTS (
                          SELECT 1
                          FROM workthread_participants wtp2
                          JOIN actors a2 ON a2.id = wtp2.actor_id
                          WHERE wtp2.thread_id = wt.id
                            AND (
                              lower(COALESCE(a2.client_name, '')) LIKE ?
                              OR lower(COALESCE(a2.agent_label, '')) LIKE ?
                              OR lower(COALESCE(a2.model_source, '')) LIKE ?
                              OR lower(COALESCE(a2.session_id, '')) LIKE ?
                            )
                        )
                        """
                    )
                    params.extend([agent_needle, agent_needle, agent_needle, agent_needle])
                if date_from:
                    clauses.append("wt.updated_at >= ?")
                    params.append(date_from)
                if date_to:
                    clauses.append("wt.updated_at <= ?")
                    params.append(date_to)
                rows = conn.execute(
                    f"""
                    SELECT wt.thread_key,
                           wt.title || char(10) || COALESCE(group_concat(wtm.body, char(10)), '') AS body,
                           wt.state, wt.updated_at, p.project_key
                    FROM workthreads wt
                    JOIN projects p ON p.id = wt.project_id
                    LEFT JOIN workthread_messages wtm ON wt.id = wtm.thread_id
                    WHERE {' AND '.join(clauses)}
                    GROUP BY wt.id
                    ORDER BY wt.updated_at DESC
                    LIMIT ?
                    """,
                    (*params, limit),
                ).fetchall()
                results.extend(
                    self._search_result("WorkThread", row["thread_key"], row["body"], row["updated_at"], term, project_key=row["project_key"], state=row["state"])
                    for row in rows
                )
            if normalized_type in {None, "Event"} and not tag and not state and not slot:
                clauses = ["(lower(e.object_type) LIKE ? OR lower(COALESCE(e.object_key, '')) LIKE ? OR lower(e.action) LIKE ? OR lower(COALESCE(e.summary, '')) LIKE ?)"]
                params = [needle, needle, needle, needle]
                if project_needle:
                    clauses.append("lower(COALESCE(p.project_key, '')) LIKE ?")
                    params.append(project_needle)
                if agent_needle:
                    clauses.append("(lower(COALESCE(a.client_name, '')) LIKE ? OR lower(COALESCE(a.agent_label, '')) LIKE ? OR lower(COALESCE(a.model_source, '')) LIKE ? OR lower(COALESCE(a.session_id, '')) LIKE ?)")
                    params.extend([agent_needle, agent_needle, agent_needle, agent_needle])
                if date_from:
                    clauses.append("e.created_at >= ?")
                    params.append(date_from)
                if date_to:
                    clauses.append("e.created_at <= ?")
                    params.append(date_to)
                rows = conn.execute(
                    f"""
                    SELECT e.object_type, e.object_key, e.action, e.summary, e.created_at,
                           p.project_key
                    FROM events e
                    LEFT JOIN projects p ON p.id = e.project_id
                    LEFT JOIN actors a ON a.id = e.actor_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY e.created_at DESC
                    LIMIT ?
                    """,
                    (*params, limit),
                ).fetchall()
                results.extend(
                    self._search_result("Event", f"{row['object_type']}:{row['object_key'] or row['action']}", row["summary"] or row["action"], row["created_at"], term, project_key=row["project_key"], action=row["action"])
                    for row in rows
                )
        results.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return {
            "status": "ok",
            "storage_mode": "local",
            "query": term,
            "filters": {
                "object_type": normalized_type,
                "project": project,
                "tag": tag,
                "state": state,
                "agent": agent,
                "date_from": date_from,
                "date_to": date_to,
                "slot": slot,
            },
            "results": results[:limit],
            "result_count": min(len(results), limit),
        }

    def should_use_work_stash(self, reason: str | None, estimated_size_bytes: int | None) -> dict[str, Any]:
        if estimated_size_bytes is not None and estimated_size_bytes < 0:
            return {"should_store": False, "status": "validation_error", "message": "estimated_size_bytes must be non-negative."}
        return {
            "status": "ok",
            "storage_mode": "local",
            "should_store": True,
            "recommendation": "store_work_stash",
            "quota_status": self.list_work_stash(),
            "reason": reason,
        }

    def _thread_row(self, conn, thread_key: str):
        return conn.execute(
            """
            SELECT wt.id, wt.project_id, wt.actor_id, wt.thread_key, wt.title, wt.state,
                   wt.created_at, wt.updated_at, p.project_key
            FROM workthreads wt
            JOIN projects p ON p.id = wt.project_id
            WHERE wt.thread_key = ?
            """,
            (thread_key,),
        ).fetchone()

    def _join_work_thread(self, conn, thread_id: int, actor_id: int, role: str, now: str) -> None:
        conn.execute(
            """
            INSERT INTO workthread_participants(thread_id, actor_id, role, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(thread_id, actor_id) DO UPDATE SET
              role = CASE
                WHEN workthread_participants.role = 'creator' THEN workthread_participants.role
                ELSE excluded.role
              END
            """,
            (thread_id, actor_id, role, now),
        )

    def _insert_work_thread_message(self, conn, *, thread_id: int, actor_id: int, body: str, now: str) -> int:
        conn.execute(
            """
            INSERT INTO workthread_messages(thread_id, actor_id, body, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (thread_id, actor_id, body, now),
        )
        return int(conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])

    def _work_thread_participants(self, conn, thread_id: int) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT wtp.role, wtp.joined_at, a.client_name, a.agent_label,
                   a.model_source, a.session_id
            FROM workthread_participants wtp
            JOIN actors a ON a.id = wtp.actor_id
            WHERE wtp.thread_id = ?
            ORDER BY wtp.joined_at ASC
            """,
            (thread_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def _replace_work_thread_references(self, conn, thread_id: int, thread_key: str, now: str) -> None:
        rows = conn.execute(
            """
            SELECT wt.title AS body FROM workthreads wt WHERE wt.id = ?
            UNION ALL
            SELECT body FROM workthread_messages WHERE thread_id = ?
            """,
            (thread_id, thread_id),
        ).fetchall()
        text = "\n".join(row["body"] for row in rows)
        self._replace_text_references(conn, "WorkThread", thread_key, text, now)

    def _set_work_thread_state(self, thread_key: str, state: str) -> dict[str, Any]:
        validation_error = _validate_handle(thread_key, "thread_key")
        if validation_error:
            return {**validation_error, "storage_mode": "local", "thread_key": thread_key}
        now = _now()
        with connect(self.db_path) as conn:
            thread = self._thread_row(conn, thread_key)
            if thread is None:
                return {"status": "not_found", "storage_mode": "local", "thread_key": thread_key}
            conn.execute(
                "UPDATE workthreads SET state = ?, updated_at = ? WHERE id = ?",
                (state, now, thread["id"]),
            )
            self._record_event(conn, thread["project_id"], thread["actor_id"], "WorkThread", thread_key, state, now)
        return {
            "status": state,
            "storage_mode": "local",
            "thread_key": thread_key,
            "state": state,
            "updated_at": now,
        }

    def _references(self, conn, source_type: str, source_key: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT target_type, target_key, created_at
            FROM object_references
            WHERE source_type = ? AND source_key = ?
            ORDER BY target_type, target_key
            """,
            (source_type, source_key),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def _referenced_by(self, conn, target_type: str, target_key: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT source_type, source_key, created_at
            FROM object_references
            WHERE target_type = ? AND target_key = ?
            ORDER BY source_type, source_key
            """,
            (target_type, target_key),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def _event_rows(self, conn, *, limit: int) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT e.object_type, e.object_key, e.action, e.summary, e.created_at,
                   p.project_key, a.client_name, a.agent_label, a.model_source
            FROM events e
            LEFT JOIN projects p ON p.id = e.project_id
            LEFT JOIN actors a ON a.id = e.actor_id
            ORDER BY e.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def _boolean_baton_fields(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            **item,
            "pinned": bool(item.get("pinned")),
            "stale": bool(item.get("stale")),
            "archived": bool(item.get("archived")),
        }

    def _project_id(self, conn, project_key: str, now: str) -> int:
        conn.execute(
            """
            INSERT INTO projects(project_key, display_name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(project_key) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (project_key, project_key, now, now),
        )
        return int(conn.execute(
            "SELECT id FROM projects WHERE project_key = ?",
            (project_key,),
        ).fetchone()["id"])

    def _actor_id(
        self,
        conn,
        *,
        model_source: str | None,
        now: str,
        agent_label: str | None = None,
    ) -> int:
        client_name = os.environ.get("A2CR_CLIENT_TYPE", "mcp").strip() or "mcp"
        session_id = os.environ.get("A2CR_SESSION_ID")
        clean_agent_label = agent_label or os.environ.get("A2CR_AGENT_LABEL")
        row = conn.execute(
            """
            SELECT id FROM actors
            WHERE client_name = ?
              AND COALESCE(agent_label, '') = COALESCE(?, '')
              AND COALESCE(model_source, '') = COALESCE(?, '')
              AND COALESCE(session_id, '') = COALESCE(?, '')
            """,
            (client_name, clean_agent_label, model_source, session_id),
        ).fetchone()
        if row:
            conn.execute("UPDATE actors SET updated_at = ? WHERE id = ?", (now, row["id"]))
            return int(row["id"])
        conn.execute(
            """
            INSERT INTO actors(client_name, agent_label, model_source, session_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (client_name, clean_agent_label, model_source, session_id, now, now),
        )
        return int(conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])

    def _replace_references(self, conn, source_type: str, source_key: str, content: dict[str, Any], now: str) -> None:
        self._replace_text_references(conn, source_type, source_key, _content_text(content), now)

    def _replace_text_references(self, conn, source_type: str, source_key: str, text: str, now: str) -> None:
        conn.execute(
            "DELETE FROM object_references WHERE source_type = ? AND source_key = ?",
            (source_type, source_key),
        )
        for target_key in _reference_keys(_WORKBATON_REF, text):
            conn.execute(
                "INSERT INTO object_references(source_type, source_key, target_type, target_key, created_at) VALUES (?, ?, ?, ?, ?)",
                (source_type, source_key, "WorkBaton", target_key, now),
            )
        for target_key in _reference_keys(_WORKSTASH_REF, text):
            conn.execute(
                "INSERT INTO object_references(source_type, source_key, target_type, target_key, created_at) VALUES (?, ?, ?, ?, ?)",
                (source_type, source_key, "WorkStash", target_key, now),
            )
        for target_key in _reference_keys(_WORKTHREAD_REF, text):
            conn.execute(
                "INSERT INTO object_references(source_type, source_key, target_type, target_key, created_at) VALUES (?, ?, ?, ?, ?)",
                (source_type, source_key, "WorkThread", target_key, now),
            )

    def _record_event(self, conn, project_id: int | None, actor_id: int | None, object_type: str, object_key: str, action: str, now: str) -> None:
        conn.execute(
            """
            INSERT INTO events(project_id, actor_id, object_type, object_key, action, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, actor_id, object_type, object_key, action, f"{action} {object_type} {object_key}", now),
        )

    def _search_result(self, object_type: str, key: str, body: str, updated_at: str, term: str, **extra: Any) -> dict[str, Any]:
        lower = body.lower()
        index = lower.find(term.lower())
        if index < 0:
            snippet = body[:180]
        else:
            start = max(0, index - 80)
            end = min(len(body), index + len(term) + 100)
            snippet = body[start:end]
        return {
            "object_type": object_type,
            "handle": key,
            "updated_at": updated_at,
            "snippet": snippet.replace("\n", " ")[:220],
            **extra,
        }


def get_store() -> LocalWorkspaceStore:
    return LocalWorkspaceStore()

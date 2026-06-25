from __future__ import annotations

import json
import secrets
import socket
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from .config import local_db_path
from .store import LocalWorkspaceStore
from .workthreads_board import build_join_prompt


DEFAULT_HOST = "127.0.0.1"


def find_available_port(host: str = DEFAULT_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def create_ui_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = 0,
    db_path: Path | None = None,
    token: str | None = None,
) -> tuple[ThreadingHTTPServer, str]:
    if host not in {DEFAULT_HOST, "localhost"}:
        raise ValueError("A2CR UI binds to 127.0.0.1 or localhost only.")
    ui_token = token or secrets.token_urlsafe(24)
    store = LocalWorkspaceStore(db_path or local_db_path())
    actual_port = port or find_available_port(host)

    class A2CRUIHandler(BaseHTTPRequestHandler):
        server_version = "A2CRLocalUI/1"

        def log_message(self, format: str, *args) -> None:  # noqa: A003 - BaseHTTPRequestHandler API
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                if not self._token_valid(parsed):
                    self._redirect(f"/?token={quote(ui_token)}")
                    return
                self._html(INDEX_HTML)
                return
            if not self._token_valid(parsed):
                self._json({"status": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            if parsed.path == "/api/state":
                self._json({
                    "status": "ok",
                    "dashboard": store.dashboard(),
                    "workbatons": store.list_workbatons(include_archived=True),
                    "workstash": store.list_work_stash(),
                    "workthreads": store.list_work_threads(include_archived=True, limit=100),
                    "actors": store.list_actors(),
                    "events": store.list_events(),
                })
                return
            if parsed.path == "/api/search":
                query = parse_qs(parsed.query)
                self._json(store.search_contexts(
                    _first(query, "q"),
                    object_type=_first(query, "type") or None,
                    project=_first(query, "project") or None,
                    tag=_first(query, "tag") or None,
                    state=_first(query, "state") or None,
                    agent=_first(query, "agent") or None,
                    date_from=_first(query, "date_from") or None,
                    date_to=_first(query, "date_to") or None,
                    slot=_first(query, "slot") or None,
                    limit=_int(_first(query, "limit"), 20),
                ))
                return
            if parsed.path == "/api/export":
                self._json(store.export_workspace())
                return
            join_prompt_key = self._workthread_suffix_key(parsed.path, "join-prompt")
            if join_prompt_key is not None:
                self._json(self._join_prompt(join_prompt_key, store))
                return
            detail = self._detail(parsed.path, store)
            if detail is not None:
                self._json(detail)
                return
            self._json({"status": "not_found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if not self._token_valid(parsed):
                self._json({"status": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            body = self._read_json()
            if parsed.path == "/api/backup":
                self._json(store.backup_database())
                return
            if parsed.path == "/api/action":
                self._json(self._action(body, store))
                return
            if parsed.path == "/api/workthreads":
                self._json(self._create_work_thread(body, store))
                return
            message_key = self._workthread_suffix_key(parsed.path, "messages")
            if message_key is not None:
                self._json(self._post_work_thread_message(message_key, body, store))
                return
            self._json({"status": "not_found"}, HTTPStatus.NOT_FOUND)

        def _create_work_thread(self, body: dict, store: LocalWorkspaceStore) -> dict:
            thread_key = _text_field(body, "thread_key")
            title = _text_field(body, "title")
            if not thread_key or not title:
                return {"status": "validation_error", "message": "thread_key and title are required"}
            return store.create_work_thread(
                thread_key=thread_key,
                title=title,
                initial_message=_text_field(body, "initial_message"),
                project=_text_field(body, "project"),
                participant_label=_text_field(body, "participant_label"),
                model_source=_text_field(body, "model_source"),
            )

        def _post_work_thread_message(self, thread_key: str, body: dict, store: LocalWorkspaceStore) -> dict:
            message = _text_field(body, "body")
            if not message:
                return {"status": "validation_error", "message": "body is required"}
            return store.post_work_thread_message(
                thread_key=thread_key,
                body=message,
                participant_label=_text_field(body, "participant_label"),
                model_source=_text_field(body, "model_source"),
            )

        def _join_prompt(self, thread_key: str, store: LocalWorkspaceStore) -> dict:
            detail = store.get_work_thread(thread_key=thread_key, include_messages=False)
            if detail.get("status") != "loaded":
                return detail
            return {
                "status": "ok",
                "storage_mode": "local",
                "thread_key": detail["thread_key"],
                "prompt": build_join_prompt(
                    thread_key=detail["thread_key"],
                    title=detail["title"],
                    project_key=detail["project_key"],
                ),
            }

        def _workthread_suffix_key(self, path: str, suffix: str) -> str | None:
            prefix = "/api/workthreads/"
            suffix_path = f"/{suffix}"
            if not path.startswith(prefix) or not path.endswith(suffix_path):
                return None
            encoded_key = path[len(prefix):-len(suffix_path)]
            if not encoded_key:
                return None
            return unquote(encoded_key)

        def _detail(self, path: str, store: LocalWorkspaceStore) -> dict | None:
            prefix_handlers = {
                "/api/workbatons/": lambda key: store.get_workbaton(key),
                "/api/workstash/": lambda key: store.get_work_stash(key),
                "/api/workthreads/": lambda key: store.get_work_thread(
                    thread_key=key,
                    include_messages=True,
                    message_limit=100,
                ),
            }
            for prefix, handler in prefix_handlers.items():
                if path.startswith(prefix):
                    key = unquote(path[len(prefix):])
                    return handler(key)
            return None

        def _action(self, body: dict, store: LocalWorkspaceStore) -> dict:
            object_type = body.get("object_type")
            key = body.get("key")
            action = body.get("action")
            if not isinstance(key, str) or not isinstance(action, str):
                return {"status": "validation_error", "message": "key and action are required"}
            if object_type == "WorkBaton":
                return store.update_workbaton_state(key, action)
            if object_type == "WorkStash" and action == "delete":
                return store.delete_work_stash(key)
            if object_type == "WorkThread" and action == "close":
                return store.close_work_thread(key)
            if object_type == "WorkThread" and action == "archive":
                return store.archive_work_thread(key)
            return {"status": "validation_error", "message": "unsupported action"}

        def _token_valid(self, parsed) -> bool:
            query = parse_qs(parsed.query)
            supplied = _first(query, "token") or self.headers.get("X-A2CR-UI-Token")
            return secrets.compare_digest(supplied or "", ui_token)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}

        def _redirect(self, location: str) -> None:
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", location)
            self.end_headers()

        def _html(self, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json(self, data: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer((host, actual_port), A2CRUIHandler)
    url = f"http://{host}:{actual_port}/?token={quote(ui_token)}"
    return server, url


def _format_startup_message(*, url: str, open_browser: bool) -> str:
    browser_status = (
        "Opening your default browser now."
        if open_browser
        else "Browser auto-open is disabled by --no-browser."
    )
    return "\n".join([
        "A2CR Local UI is running.",
        f"A2CR_UI_URL={url}",
        "Open the full URL above on this computer if the browser does not appear.",
        "The ?token= value is required; a bare 127.0.0.1 URL is rejected.",
        browser_status,
        "Keep this terminal open. Press Ctrl+C to stop the UI.",
    ])


def _open_browser(url: str) -> None:
    try:
        opened = webbrowser.open(url)
    except Exception as exc:  # pragma: no cover - depends on desktop integration
        print(f"Browser auto-open failed: {exc}", flush=True)
        print("Copy and paste A2CR_UI_URL from this terminal instead.", flush=True)
        return
    if not opened:
        print("Browser auto-open did not report success.", flush=True)
        print("Copy and paste A2CR_UI_URL from this terminal instead.", flush=True)


def serve_ui(
    *,
    host: str = DEFAULT_HOST,
    port: int = 0,
    db_path: Path | None = None,
    open_browser: bool = True,
    token: str | None = None,
) -> str:
    server, url = create_ui_server(host=host, port=port, db_path=db_path, token=token)
    if open_browser:
        threading.Timer(0.2, _open_browser, args=(url,)).start()
    print(url, flush=True)
    print(_format_startup_message(url=url, open_browser=open_browser), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return url


def _first(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or [""]
    return values[0]


def _int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text_field(body: dict, key: str) -> str | None:
    value = body.get(key)
    if not isinstance(value, str):
        return None
    clean = value.strip()
    return clean or None


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A2CR Local</title>
<style>
:root {
  color-scheme: light;
  --ink: #17201c;
  --muted: #63706a;
  --line: #d7ddd9;
  --panel: #ffffff;
  --soft: #f4f7f5;
  --green: #1e6f54;
  --teal: #0f6b78;
  --amber: #9a6418;
  --red: #9f3131;
  --blue: #2f5d8c;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: var(--soft);
  font-size: 14px;
}
button, input, select {
  font: inherit;
}
button {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
}
button.primary { background: var(--green); border-color: var(--green); color: #fff; }
button.warn { border-color: #d4a256; color: var(--amber); }
button.danger { border-color: #d79b9b; color: var(--red); }
button.ghost { background: transparent; }
button:hover { filter: brightness(0.97); }
.shell {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  min-height: 100vh;
}
.nav {
  background: #17201c;
  color: #eef6f1;
  padding: 18px 14px;
}
.brand {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 20px;
}
.nav button {
  width: 100%;
  text-align: left;
  margin: 3px 0;
  background: transparent;
  color: #dfe9e4;
  border-color: transparent;
}
.nav button.active {
  background: #24342d;
  border-color: #344a41;
}
.main {
  min-width: 0;
  padding: 18px 22px 28px;
}
.topbar {
  display: flex;
  gap: 10px;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.topbar h1 {
  font-size: 22px;
  margin: 0;
}
.toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.stats {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.stat, .panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.stat {
  padding: 12px;
}
.stat .value {
  font-size: 24px;
  font-weight: 700;
  margin-top: 4px;
}
.stat .label {
  color: var(--muted);
  font-size: 12px;
}
.panel {
  margin-bottom: 14px;
  overflow: hidden;
}
.panel h2 {
  margin: 0;
  padding: 12px 14px;
  font-size: 15px;
  border-bottom: 1px solid var(--line);
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
  text-align: left;
}
th {
  color: var(--muted);
  font-size: 12px;
  background: #f9fbfa;
}
tr.clickable { cursor: pointer; }
tr.clickable:hover { background: #f2f6f4; }
.badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 2px 7px;
  border: 1px solid var(--line);
  color: var(--muted);
  font-size: 12px;
  margin: 0 4px 4px 0;
}
.badge.open { color: var(--green); border-color: #91c7b4; }
.badge.closed { color: var(--blue); border-color: #9cb9d5; }
.badge.archived, .badge.stale { color: var(--amber); border-color: #d6b57d; }
.badge.pinned { color: var(--teal); border-color: #88bfca; }
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 14px;
}
.detail {
  min-height: 360px;
}
.detail-body {
  padding: 14px;
}
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #101714;
  color: #eef6f1;
  padding: 12px;
  border-radius: 8px;
  max-height: 520px;
  overflow: auto;
}
.filters {
  display: grid;
  grid-template-columns: 2fr repeat(7, minmax(90px, 1fr));
  gap: 8px;
  padding: 12px;
}
.filters input, .filters select {
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
}
.hidden { display: none; }
.empty {
  padding: 18px;
  color: var(--muted);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 12px;
}
@media (max-width: 980px) {
  .shell { grid-template-columns: 1fr; }
  .nav { position: sticky; top: 0; z-index: 2; }
  .nav button { width: auto; }
  .stats { grid-template-columns: repeat(2, 1fr); }
  .grid { grid-template-columns: 1fr; }
  .filters { grid-template-columns: 1fr 1fr; }
}
</style>
</head>
<body>
<div class="shell">
  <aside class="nav">
    <div class="brand">A2CR Local</div>
    <button class="active" data-view="dashboard">Dashboard</button>
    <button data-view="search">Search</button>
    <button data-view="workbatons">WorkBaton</button>
    <button data-view="workstash">WorkStash</button>
    <button data-view="workthreads">WorkThreads</button>
    <button data-view="agents">Agents</button>
    <button data-view="timeline">Timeline</button>
    <button data-view="settings">Settings</button>
  </aside>
  <main class="main">
    <div class="topbar">
      <h1 id="view-title">Dashboard</h1>
      <div class="toolbar">
        <button class="primary" id="refresh">Refresh</button>
        <button id="backup">Backup</button>
        <button id="export">Export</button>
      </div>
    </div>
    <section id="content"></section>
  </main>
</div>
<script>
const token = new URLSearchParams(location.search).get("token") || "";
let state = null;
let currentView = "dashboard";

const api = async (path, options = {}) => {
  const sep = path.includes("?") ? "&" : "?";
  const res = await fetch(path + sep + "token=" + encodeURIComponent(token), {
    ...options,
    headers: {"Content-Type": "application/json", "X-A2CR-UI-Token": token, ...(options.headers || {})}
  });
  return await res.json();
};

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, ch => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
}[ch]));

const fmt = (value) => value ? String(value).replace("T", " ").replace("Z", "") : "";
const badge = (text, cls = "") => text ? `<span class="badge ${cls}">${esc(text)}</span>` : "";
const jsonBlock = (obj) => `<pre>${esc(JSON.stringify(obj, null, 2))}</pre>`;

async function loadState() {
  state = await api("/api/state");
  render();
}

function setView(view) {
  currentView = view;
  document.querySelectorAll(".nav button").forEach(btn => btn.classList.toggle("active", btn.dataset.view === view));
  document.getElementById("view-title").textContent = ({
    dashboard: "Dashboard", search: "Search", workbatons: "WorkBaton", workstash: "WorkStash",
    workthreads: "WorkThreads", agents: "Agents", timeline: "Timeline", settings: "Settings"
  })[view];
  render();
}

function render() {
  if (!state) return;
  const content = document.getElementById("content");
  if (currentView === "dashboard") content.innerHTML = renderDashboard();
  if (currentView === "search") content.innerHTML = renderSearch();
  if (currentView === "workbatons") content.innerHTML = renderWorkbatons();
  if (currentView === "workstash") content.innerHTML = renderWorkstash();
  if (currentView === "workthreads") content.innerHTML = renderWorkthreads();
  if (currentView === "agents") content.innerHTML = renderAgents();
  if (currentView === "timeline") content.innerHTML = renderTimeline();
  if (currentView === "settings") content.innerHTML = renderSettings();
}

function renderDashboard() {
  const counts = state.dashboard.counts;
  return `
    <div class="stats">
      ${stat("Projects", counts.projects)}
      ${stat("WorkBaton", counts.workbatons)}
      ${stat("WorkStash", counts.workstash_entries)}
      ${stat("WorkThreads", counts.workthreads)}
      ${stat("Events", counts.events)}
    </div>
    <div class="grid">
      <div class="panel"><h2>Projects</h2>${table(["Project", "Baton", "Stash", "Threads", "Updated"], state.dashboard.projects.map(p => [
        p.project_key, p.workbaton_count, p.workstash_count, p.workthread_count, fmt(p.updated_at)
      ]))}</div>
      <div class="panel"><h2>Recent Events</h2>${eventList(state.dashboard.recent_events)}</div>
    </div>`;
}

function stat(label, value) {
  return `<div class="stat"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div></div>`;
}

function table(headers, rows, attrs = "") {
  if (!rows.length) return `<div class="empty">No records</div>`;
  return `<table ${attrs}><thead><tr>${headers.map(h => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${
    rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join("")}</tr>`).join("")
  }</tbody></table>`;
}

function renderSearch() {
  return `
    <div class="panel">
      <div class="filters">
        <input id="q" placeholder="Query">
        <select id="type"><option value="">All</option><option>WorkBaton</option><option>WorkStash</option><option>WorkThread</option><option>Event</option></select>
        <input id="project" placeholder="Project">
        <input id="tag" placeholder="Tag">
        <select id="threadState"><option value="">State</option><option>open</option><option>closed</option><option>archived</option></select>
        <input id="agent" placeholder="Agent">
        <input id="slot" placeholder="Slot">
        <button class="primary" onclick="runSearch()">Search</button>
      </div>
      <div id="search-results" class="detail-body"></div>
    </div>`;
}

async function runSearch() {
  const params = new URLSearchParams({
    q: document.getElementById("q").value,
    type: document.getElementById("type").value,
    project: document.getElementById("project").value,
    tag: document.getElementById("tag").value,
    state: document.getElementById("threadState").value,
    agent: document.getElementById("agent").value,
    slot: document.getElementById("slot").value,
    limit: "50"
  });
  const result = await api("/api/search?" + params.toString());
  document.getElementById("search-results").innerHTML = renderSearchResults(result.results || []);
}

function renderSearchResults(results) {
  return table(["Type", "Handle", "Project", "Snippet", "Updated"], results.map(item => [
    badge(item.object_type),
    linkFor(item.object_type, item.handle),
    esc(item.project_key || ""),
    esc(item.snippet || ""),
    fmt(item.updated_at)
  ]));
}

function renderWorkbatons() {
  const rows = state.workbatons.items.map(item => [
    linkFor("WorkBaton", item.slot_name),
    esc(item.project_key || ""),
    `${item.pinned ? badge("pinned", "pinned") : ""}${item.stale ? badge("stale", "stale") : ""}${item.archived ? badge("archived", "archived") : ""}`,
    esc(item.slot_number ?? ""),
    fmt(item.updated_at)
  ]);
  return `<div class="grid"><div class="panel"><h2>Slots</h2>${table(["Slot", "Project", "State", "No.", "Updated"], rows)}</div><div class="panel detail" id="detail"><h2>Detail</h2><div class="empty">Select a Slot</div></div></div>`;
}

function renderWorkstash() {
  const rows = state.workstash.entries.map(item => [
    linkFor("WorkStash", item.entry_key),
    esc(item.project_key || ""),
    item.tags.map(t => badge(t)).join(""),
    esc(item.size_bytes),
    fmt(item.updated_at)
  ]);
  return `<div class="grid"><div class="panel"><h2>Entries</h2>${table(["Key", "Project", "Tags", "Size", "Updated"], rows)}</div><div class="panel detail" id="detail"><h2>Detail</h2><div class="empty">Select an entry</div></div></div>`;
}

function renderWorkthreads() {
  const rows = state.workthreads.threads.map(item => [
    linkFor("WorkThread", item.thread_key),
    esc(item.project_key || ""),
    badge(item.state, item.state),
    esc(item.message_count),
    esc(item.participant_count),
    fmt(item.updated_at)
  ]);
  return `<div class="grid"><div class="panel"><h2>Threads</h2>${table(["Thread", "Project", "State", "Messages", "Agents", "Updated"], rows)}</div><div class="panel detail" id="detail"><h2>Detail</h2><div class="empty">Select a thread</div></div></div>`;
}

function renderAgents() {
  return `<div class="panel"><h2>Agents</h2>${table(["Client", "Agent", "Model", "Session", "Baton", "Stash", "Thread Msg", "Updated"], state.actors.actors.map(a => [
    esc(a.client_name || ""), esc(a.agent_label || ""), esc(a.model_source || ""), esc(a.session_id || ""),
    esc(a.workbaton_count), esc(a.workstash_count), esc(a.workthread_message_count), fmt(a.updated_at)
  ]))}</div>`;
}

function renderTimeline() {
  return `<div class="panel"><h2>Timeline</h2>${eventList(state.events.events)}</div>`;
}

function renderSettings() {
  const d = state.dashboard;
  return `<div class="panel"><h2>Settings</h2><div class="detail-body">
    <p><strong>Database</strong><br>${esc(d.database_path)}</p>
    <p><strong>Size</strong><br>${esc(d.database_size_bytes)} bytes</p>
    <p><strong>Mode</strong><br>local</p>
  </div></div>`;
}

function eventList(events) {
  return table(["Object", "Action", "Project", "Summary", "Time"], events.map(e => [
    `${badge(e.object_type || "")} ${esc(e.object_key || "")}`,
    esc(e.action || ""),
    esc(e.project_key || ""),
    esc(e.summary || ""),
    fmt(e.created_at)
  ]));
}

function linkFor(type, key) {
  return `<button class="ghost" onclick="openDetail('${esc(type)}','${encodeURIComponent(key)}')">${esc(key)}</button>`;
}

async function openDetail(type, encodedKey) {
  const key = decodeURIComponent(encodedKey);
  const endpoints = {WorkBaton: "/api/workbatons/", WorkStash: "/api/workstash/", WorkThread: "/api/workthreads/"};
  const detail = await api(endpoints[type] + encodeURIComponent(key));
  const target = document.getElementById("detail");
  if (!target) return;
  target.innerHTML = `<h2>${esc(type)} Detail</h2><div class="detail-body">${detailHtml(type, detail)}</div>`;
}

function detailHtml(type, detail) {
  if (detail.status === "not_found") return `<div class="empty">Not found</div>`;
  if (type === "WorkBaton") {
    return `${batonActions(detail.slot_name, detail)}
      <p>${badge(detail.project_key || "")}${detail.pinned ? badge("pinned", "pinned") : ""}${detail.stale ? badge("stale", "stale") : ""}${detail.archived ? badge("archived", "archived") : ""}</p>
      ${jsonBlock(detail.content)}
      <h3>References</h3>${referenceList(detail.references)}
      <h3>Referenced By</h3>${referenceList(detail.referenced_by, true)}`;
  }
  if (type === "WorkStash") {
    return `<div class="actions"><button class="danger" onclick="runAction('WorkStash','${esc(detail.entry_key)}','delete')">Delete</button></div>
      <p>${badge(detail.project_key || "")}${(detail.tags || []).map(t => badge(t)).join("")}</p>
      <pre>${esc(detail.value || "")}</pre>
      <h3>Referenced By</h3>${referenceList(detail.referenced_by, true)}`;
  }
  if (type === "WorkThread") {
    return `<div class="actions"><button class="warn" onclick="runAction('WorkThread','${esc(detail.thread_key)}','close')">Close</button><button class="danger" onclick="runAction('WorkThread','${esc(detail.thread_key)}','archive')">Archive</button></div>
      <p>${badge(detail.project_key || "")}${badge(detail.state, detail.state)}</p>
      <h3>Participants</h3>${table(["Role", "Client", "Agent", "Model"], detail.participants.map(p => [esc(p.role), esc(p.client_name || ""), esc(p.agent_label || ""), esc(p.model_source || "")]))}
      <h3>Messages</h3>${detail.messages.map(m => `<p>${badge(m.agent_label || m.client_name || "agent")} ${esc(fmt(m.created_at))}</p><pre>${esc(m.body || "")}</pre>`).join("")}
      <h3>References</h3>${referenceList(detail.references)}`;
  }
  return jsonBlock(detail);
}

function batonActions(key, detail) {
  return `<div class="actions">
    <button onclick="runAction('WorkBaton','${esc(key)}','${detail.pinned ? "unpin" : "pin"}')">${detail.pinned ? "Unpin" : "Pin"}</button>
    <button class="warn" onclick="runAction('WorkBaton','${esc(key)}','${detail.stale ? "unstale" : "stale"}')">${detail.stale ? "Fresh" : "Stale"}</button>
    <button class="warn" onclick="runAction('WorkBaton','${esc(key)}','archive')">Archive</button>
    <button class="danger" onclick="runAction('WorkBaton','${esc(key)}','delete')">Delete</button>
  </div>`;
}

function referenceList(items, reverse = false) {
  if (!items || !items.length) return `<div class="empty">No records</div>`;
  return table(reverse ? ["Source", "Handle", "Time"] : ["Target", "Handle", "Time"], items.map(item => [
    badge(reverse ? item.source_type : item.target_type),
    esc(reverse ? item.source_key : item.target_key),
    fmt(item.created_at)
  ]));
}

async function runAction(objectType, key, action) {
  if (["delete", "archive"].includes(action) && !confirm(action + " " + key + "?")) return;
  const result = await api("/api/action", {method: "POST", body: JSON.stringify({object_type: objectType, key, action})});
  if (!["deleted", "archived", "pinned", "unpinned", "stale", "fresh", "closed"].includes(result.status)) alert(JSON.stringify(result));
  await loadState();
}

document.querySelectorAll(".nav button").forEach(btn => btn.addEventListener("click", () => setView(btn.dataset.view)));
document.getElementById("refresh").addEventListener("click", loadState);
document.getElementById("backup").addEventListener("click", async () => {
  const result = await api("/api/backup", {method: "POST", body: "{}"});
  alert(result.backup_path || JSON.stringify(result));
});
document.getElementById("export").addEventListener("click", async () => {
  const result = await api("/api/export");
  const blob = new Blob([JSON.stringify(result, null, 2)], {type: "application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "a2cr-export.json";
  a.click();
  URL.revokeObjectURL(a.href);
});
loadState();
</script>
</body>
</html>
"""

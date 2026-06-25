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
<title>A2CR</title>
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
  display: flex;
  flex-direction: column;
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
.lang-switcher {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid #344a41;
}
.lang-switcher > span {
  display: block;
  font-size: 10px;
  color: #63706a;
  margin-bottom: 6px;
}
.lang-toggle {
  display: flex;
  border: 1px solid #344a41;
  border-radius: 5px;
  overflow: hidden;
}
.lang-toggle button {
  flex: 1;
  text-align: center;
  padding: 4px 0;
  font-size: 11px;
  background: transparent;
  color: #aaa;
  border: none;
  border-radius: 0;
}
.lang-toggle button.active {
  background: var(--green);
  color: #fff;
  font-weight: 600;
}
.help-steps {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 14px;
  align-items: start;
  margin-bottom: 10px;
}
.help-step-arrow {
  padding-top: 14px;
  font-size: 20px;
  color: var(--muted);
}
.help-step {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
  text-align: center;
}
.help-step-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--green);
}
.help-step-label {
  font-size: 14px;
  font-weight: 600;
}
.help-step-sub {
  font-size: 11px;
  color: var(--muted);
}
.help-detail {
  border-top: 2px solid var(--line);
  margin-top: 10px;
  padding-top: 14px;
}
.help-prompt {
  background: #101714;
  color: #eef6f1;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 12px;
  margin: 8px 0 0;
}
.help-prompt li {
  margin-bottom: 4px;
}
.views-grid {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 8px 16px;
  align-items: baseline;
}
.views-grid dt {
  font-weight: 600;
  font-size: 13px;
}
.views-grid dd {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}
.act-badge {
  display: inline-block;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
}
.act-green  { background: #d4edda; color: #1a5c2f; }
.act-red    { background: #fde8e8; color: #9f3131; }
.act-amber  { background: #fff8e6; color: #9a6418; }
.act-neutral{ background: #f4f7f5; color: #63706a; }
.badge.WorkBaton  { background: #e8f5f0; color: var(--green);  border-color: #91c7b4; }
.badge.WorkStash  { background: #fef3e2; color: var(--amber);  border-color: #d6b57d; }
.badge.WorkThread { background: #e8f2f7; color: var(--blue);   border-color: #9cb9d5; }
</style>
</head>
<body>
<div class="shell">
  <aside class="nav">
    <div class="brand">A2CR</div>
    <button class="active" data-view="dashboard">Dashboard</button>
    <button data-view="search">Search</button>
    <button data-view="workbatons">WorkBaton</button>
    <button data-view="workstash">WorkStash</button>
    <button data-view="workthreads">WorkThreads</button>
    <button data-view="agents">Agents</button>
    <button data-view="timeline">Timeline</button>
    <button data-view="settings">Settings</button>
    <button data-view="help">Help</button>
    <div class="lang-switcher">
      <span>Language</span>
      <div class="lang-toggle">
        <button id="lang-ja" class="active" onclick="setLang('ja')">日本語</button>
        <button id="lang-en" onclick="setLang('en')">English</button>
      </div>
    </div>
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
let lang = "ja";

const TITLES = {
  ja: {dashboard:"ダッシュボード", search:"検索", workbatons:"WorkBaton",
       workstash:"WorkStash", workthreads:"WorkThreads", agents:"Agents",
       timeline:"Timeline", settings:"Settings", help:"使い方ガイド"},
  en: {dashboard:"Dashboard", search:"Search", workbatons:"WorkBaton",
       workstash:"WorkStash", workthreads:"WorkThreads", agents:"Agents",
       timeline:"Timeline", settings:"Settings", help:"User Guide"}
};

function setLang(l) {
  lang = l;
  localStorage.setItem("a2cr_lang", l);
  document.getElementById("lang-ja").classList.toggle("active", l === "ja");
  document.getElementById("lang-en").classList.toggle("active", l === "en");
  document.getElementById("view-title").textContent = TITLES[lang][currentView] || currentView;
  render();
}

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
const fmtSize = (bytes) => {
  if (!bytes && bytes !== 0) return "";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
};
const badge = (text, cls = "") => text ? `<span class="badge ${cls}">${esc(text)}</span>` : "";
const actionBadge = (action) => {
  const ja = lang === "ja";
  const labels = {save: ja?"保存":"save", store: ja?"保存":"store",
    delete: ja?"削除":"delete", archive: ja?"アーカイブ":"archive",
    load: ja?"読み込み":"load", resume: ja?"読み込み":"resume"};
  const label = labels[action] || action;
  const cls = ["save","store","create","post_message"].includes(action) ? "act-green"
    : ["delete","archive"].includes(action) ? "act-red"
    : ["stale","close"].includes(action) ? "act-amber" : "act-neutral";
  return `<span class="act-badge ${cls}">${esc(label)}</span>`;
};
const jsonBlock = (obj) => `<pre>${esc(JSON.stringify(obj, null, 2))}</pre>`;

async function loadState() {
  state = await api("/api/state");
  render();
}

function setView(view) {
  currentView = view;
  document.querySelectorAll(".nav button[data-view]").forEach(btn => btn.classList.toggle("active", btn.dataset.view === view));
  document.getElementById("view-title").textContent = TITLES[lang][view] || view;
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
  if (currentView === "help") content.innerHTML = renderHelp();
}

function renderDashboard() {
  const ja = lang === "ja";
  const counts = state.dashboard.counts;
  return `
    <div class="stats">
      ${stat(ja?"プロジェクト":"Projects", counts.projects)}
      ${stat("WorkBaton", counts.workbatons)}
      ${stat("WorkStash", counts.workstash_entries)}
      ${stat("WorkThreads", counts.workthreads)}
      ${stat(ja?"イベント":"Events", counts.events)}
    </div>
    <div class="grid">
      <div class="panel"><h2>${ja?"プロジェクト":"Projects"}</h2>${table(
        [ja?"プロジェクト":"Project","WorkBaton","WorkStash","Threads",ja?"更新日時":"Updated"],
        state.dashboard.projects.map(p => [
          esc(p.project_key), esc(p.workbaton_count), esc(p.workstash_count),
          esc(p.workthread_count), fmt(p.updated_at)
        ])
      )}</div>
      <div class="panel"><h2>${ja?"最近のイベント":"Recent Events"}</h2>${eventList(state.dashboard.recent_events)}</div>
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

function renderHelp() {
  const ja = lang === "ja";
  return `
    <div class="panel" style="max-width:720px">
      <h2>${ja ? "A2CR とは" : "What is A2CR"}</h2>
      <div class="detail-body">
        <p>${ja
          ? "AIエージェントが保存した作業状態（WorkBaton・WorkStash・WorkThreads）をローカルで管理・閲覧するためのダッシュボードです。"
          : "A dashboard for viewing and managing AI agent work state (WorkBaton, WorkStash, WorkThreads) stored locally on your machine."}</p>
      </div>
    </div>
    <div class="panel" style="max-width:720px">
      <h2>${ja ? "基本の流れ" : "Basic Flow"}</h2>
      <div class="detail-body">
        <div class="help-steps">
          <div class="help-step">
            <div class="help-step-num">①</div>
            <div class="help-step-label">${ja ? "保存" : "Save"}</div>
            <div class="help-step-sub">${ja ? "AIにWorkBatonへ保存するよう指示する" : "Ask the AI to save to WorkBaton"}</div>
          </div>
          <div class="help-step-arrow">→</div>
          <div class="help-step">
            <div class="help-step-num">②</div>
            <div class="help-step-label">${ja ? "再開" : "Resume"}</div>
            <div class="help-step-sub">${ja ? "新しいAIセッションで「再開して」と指示する" : "Tell the AI to resume in a new session"}</div>
          </div>
        </div>
        <div class="help-detail">
          <strong>${ja ? "① 保存するには" : "① How to save"}</strong>
          <ul style="margin:8px 0;padding-left:18px;font-size:13px">
            ${ja ? `<li>作業の区切りで、AIに保存を依頼します</li>
            <li>AIが <code>save_context</code> ツールを呼び出し、WorkBatonに保存します</li>
            <li>Slot名はAIが自動で命名しますが、指定もできます</li>`
            : `<li>At a natural stopping point, ask the AI to save</li>
            <li>The AI calls <code>save_context</code> and writes a WorkBaton checkpoint</li>
            <li>The AI auto-names the Slot, but you can specify one</li>`}
          </ul>
          <div class="help-prompt"><ul style="margin:0;padding-left:16px">
            ${ja ? `<li>「ここまでの作業をWorkBatonに保存してください」</li>
            <li>「save して」</li>
            <li>「"feature-auth" というSlot名で保存して」</li>`
            : `<li>"Save the current work to WorkBaton"</li>
            <li>"save"</li>
            <li>"Save as slot 'feature-auth'"</li>`}
          </ul></div>
        </div>
        <div class="help-detail" style="margin-top:16px">
          <strong>${ja ? "② 再開するには" : "② How to resume"}</strong>
          <ul style="margin:8px 0;padding-left:18px;font-size:13px">
            ${ja ? `<li>新しいAIセッションを開き、再開を依頼します</li>
            <li>AIが <code>resume_context</code> ツールを呼び出し、前回の状態を復元します</li>
            <li>Slot名を指定すると特定の保存ポイントから再開できます</li>`
            : `<li>Open a new AI session and ask to resume</li>
            <li>The AI calls <code>resume_context</code> to restore the previous state</li>
            <li>Specify a Slot name to resume from a specific checkpoint</li>`}
          </ul>
          <div class="help-prompt"><ul style="margin:0;padding-left:16px">
            ${ja ? `<li>「前回の続きを再開して」</li>
            <li>「WorkBatonを読み込んで作業を再開してください」</li>
            <li>「"feature-auth" のSlotから再開して」</li>`
            : `<li>"Resume from last WorkBaton"</li>
            <li>"Load the WorkBaton and continue"</li>
            <li>"Resume from slot 'feature-auth'"</li>`}
          </ul></div>
        </div>
        <p style="margin-top:14px;padding:10px 14px;background:var(--soft);border-radius:6px;font-size:13px">
          💡 ${ja ? "ダッシュボードでいつでも保存済みの作業状態を確認・管理できます" : "Use the Dashboard to review and manage your saved work state at any time"}
        </p>
      </div>
    </div>
    <div class="panel" style="max-width:720px">
      <h2>${ja ? "各ビューの説明" : "Views Reference"}</h2>
      <div class="detail-body">
        <dl class="views-grid">
          <dt>Dashboard</dt><dd>${ja ? "プロジェクト一覧と最近のイベントを俯瞰する" : "Overview of projects and recent events"}</dd>
          <dt>WorkBaton</dt><dd>${ja ? "作業引き継ぎ用のチェックポイント。Slot名で保存・管理" : "Work handoff checkpoints, saved and managed by Slot name"}</dd>
          <dt>WorkStash</dt><dd>${ja ? "一時的なメモ領域。バトンから参照される補助データ" : "Temporary note area; auxiliary data referenced by WorkBaton"}</dd>
          <dt>WorkThreads</dt><dd>${ja ? "複数AIエージェントの協調作業スペース" : "Collaborative workspace for multi-agent coordination"}</dd>
          <dt>Search</dt><dd>${ja ? "プロジェクト・タグ・エージェントなどで横断検索" : "Cross-search by project, tag, agent, and more"}</dd>
        </dl>
      </div>
    </div>`;
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
  const ja = lang === "ja";
  return table(
    [ja?"対象":"Object", ja?"アクション":"Action", ja?"プロジェクト":"Project", ja?"日時":"Time"],
    events.map(e => [
      `${badge(e.object_type || "", e.object_type || "")} ${esc(e.object_key || "")}`,
      actionBadge(e.action || ""),
      esc(e.project_key || ""),
      fmt(e.created_at)
    ])
  );
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

document.querySelectorAll(".nav button[data-view]").forEach(btn => btn.addEventListener("click", () => setView(btn.dataset.view)));
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
// Initialize from localStorage
lang = localStorage.getItem("a2cr_lang") || "ja";
currentView = localStorage.getItem("a2cr_default_view") || "dashboard";
document.querySelectorAll(".nav button[data-view]").forEach(btn => btn.classList.toggle("active", btn.dataset.view === currentView));
document.getElementById("lang-ja").classList.toggle("active", lang === "ja");
document.getElementById("lang-en").classList.toggle("active", lang === "en");
document.getElementById("view-title").textContent = TITLES[lang][currentView] || currentView;
loadState();
</script>
</body>
</html>
"""

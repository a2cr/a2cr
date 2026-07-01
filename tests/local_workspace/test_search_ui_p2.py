import json
import threading
import urllib.error
import urllib.request

from a2cr_mcp.local_workspace.store import LocalWorkspaceStore
from a2cr_mcp.local_workspace.ui import _format_startup_message, create_ui_server


def seed_workspace(tmp_path, monkeypatch):
    db = tmp_path / "a2cr.db"
    store = LocalWorkspaceStore(db)
    monkeypatch.setenv("A2CR_AGENT_LABEL", "planner")
    store.save_context(
        slot_name="alpha-main",
        slot_number=1,
        content={
            "goal": "Ship alpha UI",
            "current_state": "Decision raven is accepted",
            "next_action": "Review WorkThread: alpha-thread and WorkStash: alpha-note",
        },
        original_length=120,
        compressed_tokens=20,
        model_source="codex",
    )
    monkeypatch.setenv("A2CR_PROJECT_ROOT", "alpha")
    store.store_work_stash(
        entry_key="alpha-note",
        value="Evidence raven for alpha UI",
        tags=["evidence", "ui"],
    )
    store.create_work_thread(
        thread_key="alpha-thread",
        title="Alpha UI coordination",
        initial_message="Builder checks raven evidence and WorkBaton: alpha-main.",
        project="alpha",
        participant_label="builder",
        model_source="gpt",
    )
    store.create_work_thread(
        thread_key="beta-thread",
        title="Beta backend coordination",
        initial_message="No UI work here.",
        project="beta",
        participant_label="reviewer",
        model_source="claude",
    )
    store.archive_work_thread("beta-thread")
    return db, store


def test_search_filters_project_tag_state_agent_slot_and_event(tmp_path, monkeypatch):
    _, store = seed_workspace(tmp_path, monkeypatch)

    project_results = store.search_contexts("raven", project="alpha")
    assert project_results["status"] == "ok"
    assert {item["project_key"] for item in project_results["results"]} == {"alpha"}

    tag_results = store.search_contexts("", tag="evidence")
    assert tag_results["result_count"] == 1
    assert tag_results["results"][0]["object_type"] == "WorkStash"
    assert tag_results["results"][0]["handle"] == "alpha-note"

    state_results = store.search_contexts("", object_type="WorkThread", state="archived")
    assert state_results["result_count"] == 1
    assert state_results["results"][0]["handle"] == "beta-thread"

    agent_results = store.search_contexts("", object_type="WorkThread", agent="builder")
    assert agent_results["result_count"] == 1
    assert agent_results["results"][0]["handle"] == "alpha-thread"

    slot_results = store.search_contexts("", slot="alpha-main")
    assert slot_results["result_count"] == 1
    assert slot_results["results"][0]["object_type"] == "WorkBaton"

    event_results = store.search_contexts("save", object_type="Event")
    assert event_results["result_count"] >= 1
    assert event_results["results"][0]["object_type"] == "Event"


def test_workbaton_safe_actions_backup_and_export(tmp_path, monkeypatch):
    _, store = seed_workspace(tmp_path, monkeypatch)

    pinned = store.update_workbaton_state("alpha-main", "pin")
    assert pinned["status"] == "pinned"
    detail = store.get_workbaton("alpha-main")
    assert detail["pinned"] is True
    assert {"target_type": "WorkThread", "target_key": "alpha-thread"} in [
        {"target_type": item["target_type"], "target_key": item["target_key"]}
        for item in detail["references"]
    ]

    stale = store.update_workbaton_state("alpha-main", "stale")
    assert stale["status"] == "stale"
    archived = store.update_workbaton_state("alpha-main", "archive")
    assert archived["status"] == "archived"

    exported = store.export_workspace()
    assert exported["status"] == "ok"
    assert len(exported["workbatons"]) == 1
    assert len(exported["workthreads"]) == 2

    backup = store.backup_database()
    assert backup["status"] == "backed_up"
    assert backup["backup_path"].endswith(".db")


def test_ui_server_serves_html_api_details_actions_and_auth(tmp_path, monkeypatch):
    db, _ = seed_workspace(tmp_path, monkeypatch)
    server, url = create_ui_server(db_path=db, token="test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        html = urllib.request.urlopen(url, timeout=5).read().decode("utf-8")
        assert "<title>A2CR</title>" in html
        assert "/api/state" in html
        assert "a2cr_timezone" in html
        assert "a2cr_selected_project" in html
        assert 'data-view="projects"' in html
        assert "All projects" in html
        assert "function renderProjects" in html
        assert "function createProjectThread" in html
        assert "function copyJoinPrompt" in html
        assert "Display time zone" in html
        assert "Asia/Tokyo" in html
        assert "Stored timestamps remain UTC" in html

        state = get_json(url, "/api/state")
        assert state["dashboard"]["counts"]["workbatons"] == 1
        assert state["workthreads"]["thread_count"] == 2
        assert {"alpha", "beta"} <= {item["project_key"] for item in state["dashboard"]["projects"]}

        detail = get_json(url, "/api/workthreads/alpha-thread")
        assert detail["status"] == "loaded"
        assert detail["message_count"] == 1
        assert detail["participants"][0]["agent_label"] == "builder"

        action = post_json(url, "/api/action", {
            "object_type": "WorkBaton",
            "key": "alpha-main",
            "action": "pin",
        })
        assert action["status"] == "pinned"

        backup = post_json(url, "/api/backup", {})
        assert backup["status"] == "backed_up"

        exported = get_json(url, "/api/export")
        assert exported["status"] == "ok"
        assert len(exported["workstash_entries"]) == 1

        created = post_json(url, "/api/workthreads", {
            "thread_key": "alpha-review",
            "title": "Alpha review",
            "project": "alpha",
            "participant_label": "planner",
            "initial_message": "Review project-centered dashboard state.",
        })
        assert created["status"] == "created"
        updated_state = get_json(url, "/api/state")
        assert any(
            item["thread_key"] == "alpha-review" and item["project_key"] == "alpha"
            for item in updated_state["workthreads"]["threads"]
        )

        try:
            urllib.request.urlopen(base(url) + "/api/state?token=wrong", timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("wrong UI token should be rejected")
    finally:
        server.shutdown()
        server.server_close()


def test_ui_startup_message_tells_users_how_to_open_fallback_url():
    url = "http://127.0.0.1:50895/?token=test-token"

    message = _format_startup_message(url=url, open_browser=True)

    assert "A2CR Local UI is running." in message
    assert f"A2CR_UI_URL={url}" in message
    assert "if the browser does not appear" in message
    assert "?token=" in message
    assert "bare 127.0.0.1 URL is rejected" in message
    assert "Ctrl+C" in message
    assert "--no-browser" not in message


def test_ui_startup_message_explains_no_browser_mode():
    url = "http://127.0.0.1:50895/?token=test-token"

    message = _format_startup_message(url=url, open_browser=False)

    assert f"A2CR_UI_URL={url}" in message
    assert "Browser auto-open is disabled by --no-browser." in message


def get_json(base_url, path):
    sep = "&" if "?" in path else "?"
    token = base_url.split("token=", 1)[1]
    with urllib.request.urlopen(base(base_url) + path + sep + "token=" + token, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(base_url, path, body):
    token = base_url.split("token=", 1)[1]
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        base(base_url) + path + "?token=" + token,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def base(base_url):
    return base_url.split("/?", 1)[0]

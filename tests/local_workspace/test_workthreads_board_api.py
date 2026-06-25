import json
import threading
import urllib.error
import urllib.request

from a2cr_mcp.local_workspace.store import LocalWorkspaceStore
from a2cr_mcp.local_workspace.ui import create_ui_server
from a2cr_mcp.local_workspace.workthreads_board import build_join_prompt


def test_join_prompt_helper_includes_room_context_and_posting_rules():
    prompt = build_join_prompt(
        thread_key="thread-alpha",
        title="Alpha coordination",
        project_key="alpha",
        participant_label="reviewer",
    )

    assert "thread-alpha" in prompt
    assert "Alpha coordination" in prompt
    assert "project: alpha" in prompt
    assert 'get_work_thread(thread_key="thread-alpha")' in prompt
    assert "post_work_thread_message(" in prompt
    assert 'participant_label="reviewer"' in prompt
    assert "Every board post is visible to the user" in prompt
    assert "WorkBaton is the compact resume artifact" in prompt
    assert "Put long supporting details in WorkStash" in prompt


def test_ui_create_room_endpoint_creates_workthread_in_temporary_db(tmp_path):
    db = tmp_path / "a2cr.db"
    server, url = create_ui_server(db_path=db, token="test-token")
    thread = start_server(server)
    try:
        result = post_json(url, "/api/workthreads", {
            "thread_key": "board-alpha",
            "title": "Board alpha",
            "project": "alpha",
            "initial_message": "Status: started",
            "participant_label": "commander",
        })

        assert result["status"] == "created"
        store = LocalWorkspaceStore(db)
        loaded = store.get_work_thread(thread_key="board-alpha")
        assert loaded["status"] == "loaded"
        assert loaded["title"] == "Board alpha"
        assert loaded["project_key"] == "alpha"
        assert loaded["message_count"] == 1
    finally:
        stop_server(server, thread)


def test_ui_message_endpoint_posts_and_registers_participant(tmp_path):
    db = tmp_path / "a2cr.db"
    store = LocalWorkspaceStore(db)
    store.create_work_thread(
        thread_key="board-beta",
        title="Board beta",
        project="beta",
        participant_label="commander",
    )
    server, url = create_ui_server(db_path=db, token="test-token")
    thread = start_server(server)
    try:
        result = post_json(url, "/api/workthreads/board-beta/messages", {
            "body": "Status: joined\nSummary: I can review the beta room.",
            "participant_label": "reviewer",
        })

        assert result["status"] == "posted"
        loaded = store.get_work_thread(thread_key="board-beta")
        assert loaded["message_count"] == 1
        assert {item["agent_label"] for item in loaded["participants"]} == {"commander", "reviewer"}
    finally:
        stop_server(server, thread)


def test_ui_join_prompt_endpoint_returns_not_found_for_missing_room(tmp_path):
    server, url = create_ui_server(db_path=tmp_path / "a2cr.db", token="test-token")
    thread = start_server(server)
    try:
        result = get_json(url, "/api/workthreads/missing-room/join-prompt")

        assert result["status"] == "not_found"
        assert result["thread_key"] == "missing-room"
    finally:
        stop_server(server, thread)


def test_ui_workthread_endpoints_reject_wrong_token(tmp_path):
    server, url = create_ui_server(db_path=tmp_path / "a2cr.db", token="test-token")
    thread = start_server(server)
    try:
        request = urllib.request.Request(
            base(url) + "/api/workthreads?token=wrong",
            data=json.dumps({"thread_key": "denied", "title": "Denied"}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("wrong UI token should be rejected")
    finally:
        stop_server(server, thread)


def start_server(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


def stop_server(server, thread):
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


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

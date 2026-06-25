import importlib
import sys


def load_server(monkeypatch, tmp_path):
    monkeypatch.setenv("A2CR_MODE", "local")
    monkeypatch.setenv("A2CR_LOCAL_DB", str(tmp_path / "a2cr.db"))
    sys.modules.pop("a2cr_mcp.server", None)
    return importlib.import_module("a2cr_mcp.server")


def fail_http_client():
    class FailClient:
        def __enter__(self):
            raise AssertionError("local WorkThreads should not open httpx.Client")

    return FailClient


def test_local_workthreads_lifecycle_references_and_search(tmp_path, monkeypatch):
    server = load_server(monkeypatch, tmp_path)
    monkeypatch.setattr(server.httpx, "Client", fail_http_client())

    created = server.create_work_thread(
        "thread-alpha",
        "Coordinate alpha work",
        initial_message="Start from WorkBaton: alpha-slot and use WorkStash: alpha-note.",
        project="alpha",
        participant_label="planner",
        model_source="codex",
    )

    assert created["status"] == "created"
    assert created["storage_mode"] == "local"
    assert created["thread_key"] == "thread-alpha"
    assert created["message_count"] == 1

    posted = server.post_work_thread_message(
        "thread-alpha",
        "Builder confirms the alpha handoff and updates WorkStash: alpha-note.",
        participant_label="builder",
        model_source="gpt",
    )
    assert posted["status"] == "posted"
    assert posted["message_id"] > 0

    listed = server.list_work_threads()
    assert listed["status"] == "ok"
    assert listed["thread_count"] == 1
    assert listed["threads"][0]["thread_key"] == "thread-alpha"
    assert listed["threads"][0]["state"] == "open"
    assert listed["threads"][0]["message_count"] == 2
    assert listed["threads"][0]["participant_count"] == 2

    loaded = server.get_work_thread("thread-alpha")
    assert loaded["status"] == "loaded"
    assert loaded["project_key"] == "alpha"
    assert loaded["message_count"] == 2
    assert loaded["messages_returned"] == 2
    assert {participant["agent_label"] for participant in loaded["participants"]} == {"planner", "builder"}
    assert {"target_type": "WorkBaton", "target_key": "alpha-slot"} in [
        {"target_type": item["target_type"], "target_key": item["target_key"]}
        for item in loaded["references"]
    ]
    assert {"target_type": "WorkStash", "target_key": "alpha-note"} in [
        {"target_type": item["target_type"], "target_key": item["target_key"]}
        for item in loaded["references"]
    ]

    search = server.search_contexts("Builder", object_type="WorkThread")
    assert search["status"] == "ok"
    assert search["results"][0]["object_type"] == "WorkThread"
    assert search["results"][0]["handle"] == "thread-alpha"

    closed = server.close_work_thread("thread-alpha")
    assert closed["status"] == "closed"
    blocked_post = server.post_work_thread_message("thread-alpha", "late message")
    assert blocked_post["status"] == "thread_not_open"

    archived = server.archive_work_thread("thread-alpha")
    assert archived["status"] == "archived"
    assert server.list_work_threads()["thread_count"] == 0
    archived_list = server.list_work_threads(include_archived=True)
    assert archived_list["thread_count"] == 1
    assert archived_list["threads"][0]["state"] == "archived"


def test_local_workthreads_truncate_long_messages(tmp_path, monkeypatch):
    server = load_server(monkeypatch, tmp_path)
    monkeypatch.setattr(server.httpx, "Client", fail_http_client())

    server.create_work_thread("thread-long", "Long coordination")
    server.post_work_thread_message("thread-long", "x" * 2000, participant_label="writer")

    loaded = server.get_work_thread("thread-long")

    assert loaded["status"] == "loaded"
    assert loaded["messages"][0]["truncated"] is True
    assert len(loaded["messages"][0]["body"]) < 2000
    assert loaded["messages"][0]["original_length"] == 2000


def test_default_mode_workthreads_use_local_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("A2CR_LOCAL_DB", str(tmp_path / "a2cr.db"))
    monkeypatch.delenv("A2CR_MODE", raising=False)
    sys.modules.pop("a2cr_mcp.server", None)
    server = importlib.import_module("a2cr_mcp.server")
    monkeypatch.setattr(server.httpx, "Client", fail_http_client())

    result = server.create_work_thread("thread-default", "Default local mode")

    assert result["status"] == "created"
    assert result["storage_mode"] == "local"

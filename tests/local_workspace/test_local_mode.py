import importlib
import sys


CONTENT = {
    "goal": "local save",
    "current_state": "roundtrip with local sqlite",
    "next_action": "load the baton",
    "references": ["WorkStash: local-note"],
}


def load_server(monkeypatch, tmp_path):
    monkeypatch.setenv("A2CR_MODE", "local")
    monkeypatch.setenv("A2CR_LOCAL_DB", str(tmp_path / "a2cr.db"))
    sys.modules.pop("a2cr_mcp.server", None)
    return importlib.import_module("a2cr_mcp.server")


def fail_http_client():
    class FailClient:
        def __enter__(self):
            raise AssertionError("local mode should not open httpx.Client")

    return FailClient


def test_local_mode_workbaton_roundtrip_without_http(tmp_path, monkeypatch):
    server = load_server(monkeypatch, tmp_path)
    monkeypatch.setattr(server.httpx, "Client", fail_http_client())

    saved = server.save_context(
        "demo-main",
        CONTENT,
        model_source="codex",
        slot_number=1,
        preferred_response_language="ja",
    )

    assert saved["status"] == "saved"
    assert saved["storage_mode"] == "local"
    assert saved["slot_name"] == "demo-main"
    assert saved["slot_number"] == 1
    assert saved["agent_continuity_guidance"]["use_proactively"] is True
    assert saved["response_language_hint"] == "ja"

    listed = server.list_contexts()
    assert listed[0]["slot_name"] == "demo-main"
    assert listed[0]["storage_mode"] == "local"

    loaded = server.load_context(slot_number=1)
    assert loaded["status"] == "loaded"
    assert loaded["storage_mode"] == "local"
    assert loaded["content"]["goal"] == "local save"
    assert loaded["content"]["language_context"]["preferred_response_language"] == "ja"
    assert loaded["agent_continuity_guidance"]["use_proactively"] is True

    resumed = server.resume_context(project="demo", prefer_latest=True)
    assert resumed["status"] == "loaded"
    assert resumed["slot_name"] == "demo-main"

    handoff = server.get_handoff("demo-main")
    assert handoff["slot_name"] == "demo-main"
    assert "local save" in handoff["handoff_text"]


def test_local_mode_workstash_search_and_delete_without_http(tmp_path, monkeypatch):
    server = load_server(monkeypatch, tmp_path)
    monkeypatch.setattr(server.httpx, "Client", fail_http_client())

    stash = server.store_work_stash(
        "local-note",
        "SQLite search evidence",
        tags=["local", "evidence"],
        project="demo",
    )
    assert stash["status"] == "stored"
    assert stash["storage_mode"] == "local"
    assert stash["project_key"] == "demo"

    loaded = server.get_work_stash("local-note")
    assert loaded["status"] == "loaded"
    assert loaded["value"] == "SQLite search evidence"
    assert loaded["tags"] == ["local", "evidence"]
    assert loaded["project_key"] == "demo"

    entries = server.list_work_stash(tag_filter="local")
    assert entries["entry_count"] == 1
    assert entries["entries"][0]["entry_key"] == "local-note"
    assert entries["entries"][0]["project_key"] == "demo"

    server.save_context("demo-main", CONTENT, model_source="codex")
    search = server.search_contexts("SQLite", project="demo")
    assert search["status"] == "ok"
    assert search["storage_mode"] == "local"
    assert {item["object_type"] for item in search["results"]} >= {"WorkBaton", "WorkStash"}

    deleted = server.delete_work_stash("local-note")
    assert deleted == {"status": "deleted", "storage_mode": "local", "entry_key": "local-note"}


def test_local_mode_account_limits_and_stash_advice(tmp_path, monkeypatch):
    server = load_server(monkeypatch, tmp_path)
    monkeypatch.setattr(server.httpx, "Client", fail_http_client())

    limits = server.get_account_limits()
    assert limits["storage_mode"] == "local"
    assert limits["requires_api_key"] is False
    assert limits["database_path"].endswith("a2cr.db")

    advice = server.should_use_work_stash(reason="confirmed file paths", estimated_size_bytes=123)
    assert advice["status"] == "ok"
    assert advice["storage_mode"] == "local"
    assert advice["should_store"] is True

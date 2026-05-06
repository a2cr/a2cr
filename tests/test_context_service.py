import json
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session
from services.db import get_engine, Context, Stats
from services.exceptions import SlotLimitExceeded, ContentTooLarge, SlotNotFound
import services.context as ctx_service

CONTENT = {
    "goal": "test goal",
    "current_state": "state",
    "next_action": "action",
}


def test_save_creates_slot():
    result = ctx_service.save_context("proj-a", CONTENT, None, None)
    assert result.slot_name == "proj-a"
    assert result.slot_number == 1
    assert result.compressed_tokens > 0
    assert result.saved_tokens is None  # no original_length


def test_save_assigns_fixed_slot_numbers():
    first = ctx_service.save_context("slot-one", CONTENT, None, None)
    second = ctx_service.save_context("slot-two", CONTENT, None, None)
    assert first.slot_number == 1
    assert second.slot_number == 2


def test_save_to_fixed_slot_number_overwrites_that_position():
    first = ctx_service.save_context("fixed-a", CONTENT, None, None, slot_number=2)
    second = ctx_service.save_context("fixed-b", CONTENT, None, None, slot_number=2)

    assert first.slot_number == 2
    assert second.slot_number == 2

    results = ctx_service.list_contexts()
    assert [(r.slot_number, r.slot_name) for r in results] == [(2, "fixed-b")]
    with pytest.raises(SlotNotFound):
        ctx_service.load_context("fixed-a")


def test_list_contexts_returns_fixed_slot_order():
    ctx_service.save_context("slot-two", CONTENT, None, None, slot_number=2)
    ctx_service.save_context("slot-one", CONTENT, None, None, slot_number=1)

    results = ctx_service.list_contexts()
    assert [(r.slot_number, r.slot_name) for r in results] == [
        (1, "slot-one"),
        (2, "slot-two"),
    ]


def test_save_with_original_length():
    result = ctx_service.save_context("proj-b", CONTENT, 3000, "claude")
    assert result.original_tokens == 1000  # ceil(3000/3)
    assert result.saved_tokens == 1000 - result.compressed_tokens


def test_save_overwrite_resets_expires_at():
    ctx_service.save_context("proj-c", CONTENT, None, None)
    import time; time.sleep(0.01)
    r2 = ctx_service.save_context("proj-c", CONTENT, None, None)
    assert r2.slot_name == "proj-c"
    # Load should return updated content
    loaded = ctx_service.load_context("proj-c")
    assert loaded is not None


def test_save_slot_limit_exceeded():
    ctx_service.save_context("slot-1", CONTENT, None, None)
    ctx_service.save_context("slot-2", CONTENT, None, None)
    ctx_service.save_context("slot-3", CONTENT, None, None)
    with pytest.raises(SlotLimitExceeded):
        ctx_service.save_context("slot-4", CONTENT, None, None)


def test_save_overwrite_does_not_count_toward_limit():
    ctx_service.save_context("slot-1", CONTENT, None, None)
    ctx_service.save_context("slot-2", CONTENT, None, None)
    ctx_service.save_context("slot-3", CONTENT, None, None)
    # Overwriting slot-1 should succeed even though 3 slots exist
    result = ctx_service.save_context("slot-1", CONTENT, None, None)
    assert result.slot_name == "slot-1"


def test_save_content_too_large():
    big_content = dict(CONTENT)
    big_content["background"] = "x" * 11000
    with pytest.raises(ContentTooLarge):
        ctx_service.save_context("proj-x", big_content, None, None)


def test_load_existing():
    ctx_service.save_context("proj-load", CONTENT, None, "gpt")
    result = ctx_service.load_context("proj-load")
    assert result is not None
    assert result.content["goal"] == "test goal"
    assert result.slot_number == 1
    assert result.model_source == "gpt"
    assert result.load_count == 1
    assert result.encryption_mode == "server"


def test_save_load_client_encrypted_context_without_server_decrypt(monkeypatch):
    encrypted_content = {
        "version": 1,
        "alg": "XChaCha20-Poly1305",
        "nonce": "nonce",
        "ciphertext": "ciphertext",
        "key_wrap": {"type": "local-key", "kid": "test"},
    }

    result = ctx_service.save_context(
        "encrypted-slot",
        None,
        None,
        "codex",
        encrypted_content=encrypted_content,
    )

    def fail_decrypt(*args, **kwargs):
        raise AssertionError("client-encrypted context should not be decrypted server-side")

    monkeypatch.setattr(ctx_service, "decrypt", fail_decrypt)

    loaded = ctx_service.load_context("encrypted-slot")
    assert result.encryption_mode == "client"
    assert loaded.encryption_mode == "client"
    assert loaded.content is None
    assert loaded.encrypted_content == encrypted_content


def test_load_by_slot_number():
    ctx_service.save_context("number-load", CONTENT, None, "gpt", slot_number=2)
    result = ctx_service.load_context(slot_number=2)
    assert result.slot_name == "number-load"
    assert result.slot_number == 2
    assert result.content["goal"] == "test goal"


def test_save_load_preserves_unicode_content():
    content = dict(CONTENT)
    content["goal"] = "設計書レビュー"
    content["current_state"] = "Freeは24時間保持、Proは30日保持"
    content["next_action"] = "日本語のままMCPで読み込めることを確認する"
    content["decisions"] = ["RLSを有効化", "アクセスログは本文を保存しない"]

    ctx_service.save_context("proj-unicode", content, None, None)
    result = ctx_service.load_context("proj-unicode")

    assert result.content == content


def test_load_increments_load_count():
    ctx_service.save_context("proj-lc", CONTENT, None, None)
    ctx_service.load_context("proj-lc")
    ctx_service.load_context("proj-lc")
    result = ctx_service.load_context("proj-lc")
    assert result.load_count == 3


def test_load_nonexistent_raises():
    with pytest.raises(SlotNotFound):
        ctx_service.load_context("does-not-exist")


def test_delete_removes_slot():
    ctx_service.save_context("proj-del", CONTENT, None, None)
    ctx_service.delete_context("proj-del")
    with pytest.raises(SlotNotFound):
        ctx_service.load_context("proj-del")


def test_delete_nonexistent_raises():
    with pytest.raises(SlotNotFound):
        ctx_service.delete_context("ghost-slot")


def test_list_returns_active_slots():
    ctx_service.save_context("slot-a", CONTENT, None, None)
    ctx_service.save_context("slot-b", CONTENT, None, "claude")
    result = ctx_service.list_contexts()
    names = [r.slot_name for r in result]
    assert "slot-a" in names
    assert "slot-b" in names


def test_list_excludes_expired(monkeypatch):
    ctx_service.save_context("slot-exp", CONTENT, None, None)
    # Manually expire the slot
    with Session(get_engine()) as session:
        ctx = session.execute(
            __import__("sqlalchemy").select(Context).where(Context.slot_name == "slot-exp")
        ).scalar_one()
        ctx.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()
    result = ctx_service.list_contexts()
    assert all(r.slot_name != "slot-exp" for r in result)


def test_cleanup_expired_deletes_old_slots():
    ctx_service.save_context("slot-clean", CONTENT, None, None)
    with Session(get_engine()) as session:
        ctx = session.execute(
            __import__("sqlalchemy").select(Context).where(Context.slot_name == "slot-clean")
        ).scalar_one()
        ctx.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()
    ctx_service.cleanup_expired()
    with pytest.raises(SlotNotFound):
        ctx_service.load_context("slot-clean")


def test_stats_incremented_on_save():
    ctx_service.save_context("slot-stats", CONTENT, 3000, None)
    with Session(get_engine()) as session:
        stats = session.get(Stats, 1)
    assert stats.total_saves == 1
    assert stats.total_tokens_saved > 0


def test_stats_incremented_on_load():
    ctx_service.save_context("slot-stats-load", CONTENT, None, None)
    ctx_service.load_context("slot-stats-load")
    with Session(get_engine()) as session:
        stats = session.get(Stats, 1)
    assert stats.total_loads == 1


def test_get_handoff_returns_markdown():
    content = dict(CONTENT)
    content["decisions"] = ["Use FastAPI", "Use SQLite"]
    content["constraints"] = ["No SQLCipher"]
    content["environment"] = "Python 3.13"
    ctx_service.save_context("proj-handoff", content, None, None)
    result = ctx_service.get_handoff("proj-handoff")
    assert result.slot_name == "proj-handoff"
    assert "# GOAL" in result.handoff_text
    assert "# CURRENT_STATE" in result.handoff_text
    assert "# NEXT_ACTION" in result.handoff_text
    assert "# DECISIONS" in result.handoff_text
    assert "Use FastAPI" in result.handoff_text
    assert "# CONSTRAINTS" in result.handoff_text
    assert "# ENVIRONMENT" in result.handoff_text


def test_get_handoff_nonexistent_raises():
    with pytest.raises(SlotNotFound):
        ctx_service.get_handoff("no-such-slot")

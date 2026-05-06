from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session
from services.db import get_engine, Context, Stats
from services.exceptions import AppError, SlotLimitExceeded, ContentTooLarge, SlotNotFound
import services.context as ctx_service

CONTENT = {
    "goal": "test goal",
    "current_state": "state",
    "next_action": "action",
}


def encrypted(label: str = "ciphertext") -> dict:
    return {
        "version": 1,
        "alg": "Fernet",
        "nonce": "embedded",
        "ciphertext": label,
        "key_wrap": {"type": "local-key", "kid": "test"},
    }


def save_slot(
    slot_name: str,
    original_length=None,
    model_source=None,
    slot_number=None,
    payload: dict | None = None,
):
    return ctx_service.save_context(
        slot_name,
        None,
        original_length,
        model_source,
        slot_number=slot_number,
        encrypted_content=payload or encrypted(slot_name),
    )


def test_save_creates_slot():
    result = save_slot("proj-a")
    assert result.slot_name == "proj-a"
    assert result.slot_number == 1
    assert result.compressed_tokens > 0
    assert result.saved_tokens is None  # no original_length


def test_save_assigns_fixed_slot_numbers():
    first = save_slot("slot-one")
    second = save_slot("slot-two")
    assert first.slot_number == 1
    assert second.slot_number == 2


def test_save_to_fixed_slot_number_overwrites_that_position():
    first = save_slot("fixed-a", slot_number=2)
    second = save_slot("fixed-b", slot_number=2)

    assert first.slot_number == 2
    assert second.slot_number == 2

    results = ctx_service.list_contexts()
    assert [(r.slot_number, r.slot_name) for r in results] == [(2, "fixed-b")]
    with pytest.raises(SlotNotFound):
        ctx_service.load_context("fixed-a")


def test_list_contexts_returns_fixed_slot_order():
    save_slot("slot-two", slot_number=2)
    save_slot("slot-one", slot_number=1)

    results = ctx_service.list_contexts()
    assert [(r.slot_number, r.slot_name) for r in results] == [
        (1, "slot-one"),
        (2, "slot-two"),
    ]


def test_save_with_original_length():
    result = save_slot("proj-b", 3000, "claude")
    assert result.original_tokens == 1000  # ceil(3000/3)
    assert result.saved_tokens == 1000 - result.compressed_tokens


def test_save_overwrite_resets_expires_at():
    save_slot("proj-c")
    import time; time.sleep(0.01)
    r2 = save_slot("proj-c")
    assert r2.slot_name == "proj-c"
    # Load should return updated content
    loaded = ctx_service.load_context("proj-c")
    assert loaded is not None


def test_save_slot_limit_exceeded():
    save_slot("slot-1")
    save_slot("slot-2")
    save_slot("slot-3")
    with pytest.raises(SlotLimitExceeded):
        save_slot("slot-4")


def test_save_overwrite_does_not_count_toward_limit():
    save_slot("slot-1")
    save_slot("slot-2")
    save_slot("slot-3")
    # Overwriting slot-1 should succeed even though 3 slots exist
    result = save_slot("slot-1")
    assert result.slot_name == "slot-1"


def test_save_content_too_large():
    with pytest.raises(ContentTooLarge):
        save_slot("proj-x", payload=encrypted("x" * 11000))


def test_load_existing():
    payload = encrypted("proj-load")
    save_slot("proj-load", model_source="gpt", payload=payload)
    result = ctx_service.load_context("proj-load")
    assert result is not None
    assert result.content is None
    assert result.encrypted_content == payload
    assert result.slot_number == 1
    assert result.model_source == "gpt"
    assert result.load_count == 1
    assert result.encryption_mode == "client"


def test_save_load_client_encrypted_context_without_server_decrypt():
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

    loaded = ctx_service.load_context("encrypted-slot")
    assert not hasattr(ctx_service, "decrypt")
    assert result.encryption_mode == "client"
    assert loaded.encryption_mode == "client"
    assert loaded.content is None
    assert loaded.encrypted_content == encrypted_content


def test_load_by_slot_number():
    payload = encrypted("number-load")
    save_slot("number-load", model_source="gpt", slot_number=2, payload=payload)
    result = ctx_service.load_context(slot_number=2)
    assert result.slot_name == "number-load"
    assert result.slot_number == 2
    assert result.content is None
    assert result.encrypted_content == payload


def test_save_load_preserves_encrypted_payload():
    payload = encrypted("unicode-ciphertext")
    save_slot("proj-unicode", payload=payload)
    result = ctx_service.load_context("proj-unicode")

    assert result.content is None
    assert result.encrypted_content == payload


def test_load_increments_load_count():
    save_slot("proj-lc")
    ctx_service.load_context("proj-lc")
    ctx_service.load_context("proj-lc")
    result = ctx_service.load_context("proj-lc")
    assert result.load_count == 3


def test_load_nonexistent_raises():
    with pytest.raises(SlotNotFound):
        ctx_service.load_context("does-not-exist")


def test_delete_removes_slot():
    save_slot("proj-del")
    ctx_service.delete_context("proj-del")
    with pytest.raises(SlotNotFound):
        ctx_service.load_context("proj-del")


def test_delete_nonexistent_raises():
    with pytest.raises(SlotNotFound):
        ctx_service.delete_context("ghost-slot")


def test_list_returns_active_slots():
    save_slot("slot-a")
    save_slot("slot-b", model_source="claude")
    result = ctx_service.list_contexts()
    names = [r.slot_name for r in result]
    assert "slot-a" in names
    assert "slot-b" in names


def test_list_excludes_expired(monkeypatch):
    save_slot("slot-exp")
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
    save_slot("slot-clean")
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
    save_slot("slot-stats", 3000)
    with Session(get_engine()) as session:
        stats = session.get(Stats, 1)
    assert stats.total_saves == 1
    assert stats.total_tokens_saved > 0


def test_stats_incremented_on_load():
    save_slot("slot-stats-load")
    ctx_service.load_context("slot-stats-load")
    with Session(get_engine()) as session:
        stats = session.get(Stats, 1)
    assert stats.total_loads == 1


def test_get_handoff_requires_client_decryption():
    save_slot("proj-handoff")
    with pytest.raises(AppError) as exc:
        ctx_service.get_handoff("proj-handoff")
    assert exc.value.code == "client_decryption_required"


def test_get_handoff_nonexistent_raises():
    with pytest.raises(SlotNotFound):
        ctx_service.get_handoff("no-such-slot")

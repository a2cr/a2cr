"""
Streamlit dashboard for AI Clipboard.
Reads SQLite directly; delete calls the API to keep stats consistent.
"""
import sys
from pathlib import Path
import json
from datetime import datetime, timezone, timedelta

import streamlit as st
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

# Import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.config import get_config
from services.db import get_engine, Context, Stats
from services.crypto import decrypt

st.set_page_config(page_title="AI Clipboard", layout="wide")

config = get_config()
API_BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": config.api_key}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _load_stats() -> Stats | None:
    with Session(get_engine()) as session:
        return session.get(Stats, 1)


def _load_slots() -> list[Context]:
    now = _now()
    with Session(get_engine()) as session:
        rows = session.execute(
            select(Context).where(Context.expires_at > now)
        ).scalars().all()
        # Detach from session by converting to dicts
        return [
            {
                "slot_name": r.slot_name,
                "size_bytes": r.size_bytes,
                "expires_at": r.expires_at,
                "updated_at": r.updated_at,
                "compressed_tokens": r.compressed_tokens,
                "original_tokens": r.original_tokens,
                "model_source": r.model_source,
                "load_count": r.load_count,
                "content_encrypted": r.content,
            }
            for r in rows
        ]


def _decrypt_content(encrypted: str) -> dict | None:
    try:
        return json.loads(decrypt(encrypted))
    except Exception:
        return None


def _minutes_left(expires_at: datetime) -> float:
    return max(0.0, (expires_at - _now()).total_seconds() / 60)


# ─── Auto-refresh (30s) ───────────────────────────────────────────────
st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────
st.title("AI Clipboard")

# ─── Stats ───────────────────────────────────────────────────────────
stats = _load_stats()
if stats:
    col1, col2, col3 = st.columns(3)
    col1.metric("累計保存回数", stats.total_saves)
    col2.metric("累計ロード回数", stats.total_loads)
    col3.metric("累計節約トークン（概算）", f"{stats.total_tokens_saved:,}")

st.divider()

# ─── Slot list ────────────────────────────────────────────────────────
slots = _load_slots()
st.subheader(f"現在のスロット（{len(slots)}/3 件使用中）")

if not slots:
    st.info("保存されているスロットはありません。")

for slot in slots:
    minutes = _minutes_left(slot["expires_at"])
    time_color = "orange" if minutes < 10 else "green"
    saved = (
        (slot["original_tokens"] - slot["compressed_tokens"])
        if slot["original_tokens"] is not None
        else None
    )

    with st.expander(f"**{slot['slot_name']}**  —  残り :{time_color}[{minutes:.0f}分]"):
        col_a, col_b, col_c, col_d, col_e = st.columns([2, 1, 1, 1, 1])
        col_a.write(f"モデル: `{slot['model_source'] or '—'}`")
        col_b.write(f"サイズ: {slot['size_bytes']:,} B")
        col_c.write(f"圧縮後: {slot['compressed_tokens']:,} tok")
        col_d.write(f"節約: {saved:,} tok" if saved is not None else "節約: —")
        col_e.write(f"ロード: {slot['load_count']} 回")

        # Content preview
        content = _decrypt_content(slot["content_encrypted"])
        if content:
            st.markdown("**goal:** " + content.get("goal", ""))
            st.markdown("**current_state:** " + content.get("current_state", ""))
            st.markdown("**next_action:** " + content.get("next_action", ""))
            with st.expander("すべてのフィールドを見る"):
                st.json(content)

        # Delete button
        if st.button(f"削除", key=f"del-{slot['slot_name']}"):
            r = requests.delete(
                f"{API_BASE}/v1/context/{slot['slot_name']}", headers=HEADERS, timeout=5
            )
            if r.ok:
                st.success("削除しました")
                st.rerun()
            else:
                st.error(f"削除失敗: {r.text}")

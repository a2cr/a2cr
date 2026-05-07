"""
Legacy Streamlit dashboard for the local A2CR prototype.
Reads SQLite directly; disabled unless explicitly enabled for local prototype work.
"""
import sys
from pathlib import Path
import html
import json
import os
from datetime import datetime, timezone, timedelta

import streamlit as st
import streamlit.components.v1 as components
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

# Import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.config import get_config, get_data_dir, is_legacy_local_api_enabled
from services.db import get_engine, Context, Stats, init_db
from services.crypto import decrypt

st.set_page_config(page_title="A2CR", layout="wide")

if not is_legacy_local_api_enabled():
    st.error(
        "The legacy local SQLite dashboard is disabled. "
        "Use the A2CR SaaS dashboard for normal WorkBaton usage. "
        "Set A2CR_ENABLE_LEGACY_LOCAL_API=1 only for explicit local prototype tests."
    )
    st.stop()

st.markdown("""
<style>
  .block-container { padding-top: 1.1rem !important; }
  .app-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    min-height: 2.8rem;
    padding: 0 0 0.2rem;
    overflow: visible;
  }
  .app-title {
    font-size: 1.85rem;
    font-weight: 700;
    line-height: 1.25;
  }
  .app-status {
    font-size: 1.1rem;
    line-height: 1.25;
    white-space: nowrap;
  }
  div[data-testid="stSelectbox"] { max-width: 130px !important; }
  div[data-testid="stSelectbox"] div[data-baseweb="select"] * { font-size: 0.75rem !important; }
  div[data-testid="stToggle"] label {
    white-space: nowrap !important;
  }
  div[data-testid="stButton"] button {
    min-width: 4.2rem !important;
    white-space: nowrap !important;
  }
  div[data-testid="stCodeBlock"],
  div[data-testid="stCodeBlock"] > div,
  div[data-testid="stCodeBlock"] pre {
    max-width: 100% !important;
    overflow-x: hidden !important;
  }
  div[data-testid="stCodeBlock"] pre,
  div[data-testid="stCodeBlock"] code,
  div[data-testid="stCodeBlock"] span {
    white-space: pre-wrap !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
  }
  div[data-testid="stCodeBlock"] pre {
    margin: 0.2rem 0 0.45rem !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.9rem !important;
    line-height: 1.45 !important;
  }
  div[data-testid="stCodeBlock"] code {
    display: block !important;
    min-width: 0 !important;
  }
  div[class*="st-key-slot_panel_"] {
    box-sizing: border-box;
    min-height: 100%;
    padding: 0.85rem 0.9rem;
    border: 1px solid #2e5f59;
    border-radius: 10px;
    background: #111d21;
  }
  div[class*="st-key-slot_panel_"] > div {
    background: transparent !important;
  }
  .slot-card-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.6rem;
    margin-bottom: 0.65rem;
  }
  .slot-card-title {
    flex: 0 0 auto;
    font-weight: 700;
    line-height: 1.35;
  }
  .slot-card-meta {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 0.35rem;
    min-width: 0;
    color: rgba(226, 232, 240, 0.78);
    font-size: 0.76rem;
    font-weight: 600;
    line-height: 1.35;
    text-align: right;
  }
  .slot-new-badge {
    display: inline-flex;
    align-items: center;
    min-height: 1.15rem;
    padding: 0.02rem 0.42rem;
    border-radius: 999px;
    background: #f43f5e;
    color: #ffffff;
    font-size: 0.68rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: 0;
  }
  h2, h3 {
    margin-top: 0.45rem !important;
    margin-bottom: 0.35rem !important;
  }
  hr {
    margin: 0.75rem 0 !important;
  }
  .stats-band {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
    margin: 0.55rem 0 0.8rem;
    padding: 0.75rem 1rem;
    border: 1px solid rgba(45, 212, 191, 0.34);
    border-radius: 10px;
    background: #10201f;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }
  .stats-band.stats-side {
    grid-template-columns: 1fr;
    gap: 0.85rem;
    margin: 0.2rem 0 0.45rem;
    padding: 1rem;
    position: sticky;
    top: 0.75rem;
  }
  .stats-band.stats-side .stat-card + .stat-card {
    border-top: 1px solid rgba(255, 255, 255, 0.14);
    padding-top: 0.85rem;
  }
  .stat-card {
    min-width: 0;
  }
  .stat-label {
    color: rgba(255, 255, 255, 0.88);
    font-size: 0.85rem;
    font-weight: 700;
    line-height: 1.3;
  }
  .stat-help {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1rem;
    height: 1rem;
    margin-left: 0.25rem;
    border: 1px solid rgba(255, 255, 255, 0.45);
    border-radius: 999px;
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.7rem;
  }
  .stat-value {
    margin-top: 0.2rem;
    color: #ffffff;
    font-size: 1.65rem;
    font-weight: 500;
    line-height: 1.1;
  }
  @media (max-width: 1200px) {
    .stats-band.stats-side {
      position: static;
    }
  }
  @media (max-width: 700px) {
    .stats-band { grid-template-columns: 1fr; }
  }
  @media (max-width: 1050px) {
    .st-key-header_controls,
    .st-key-header-controls {
      display: none !important;
    }
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-of-type(2),
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-of-type(3) {
      display: none !important;
    }
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:first-of-type {
      flex: 1 1 100% !important;
      width: 100% !important;
      max-width: 100% !important;
    }
    .app-header {
      min-height: 2.5rem;
    }
    .app-title {
      font-size: 1.75rem;
    }
  }
</style>
""", unsafe_allow_html=True)

init_db()

config = get_config()
API_BASE = "http://localhost:8000"
SERVICE_URL = os.environ.get("A2CR_SERVICE_URL", API_BASE)
HEADERS = {"X-API-Key": config.api_key}
AUTO_RELOAD_SECONDS = 300
SLOT_SCROLL_HEIGHT = 520
SETTINGS_PATH = get_data_dir() / "dashboard_settings.json"

# ─── Translations ─────────────────────────────────────────────────────
T = {
    "ja": {
        "server_on": "### 🟢 稼働中",
        "server_off": "### 🔴 停止中",
        "usage_label": "📖 使い方を見る",
        "usage_text": """
**A2CR** は、AIエージェントの作業文脈を一時保存し、新しい会話窓へ引き継ぐローカルMVPです。

---

#### 基本の流れ

1. Slot一覧の上にある **保存用文章** を今のAI会話へ貼る
2. AIが `save_context` で現在の作業を保存する。保存先を指定したい場合は **Slot番号** で指示できます
3. 新しい窓では、対象Slotの下にある **ロード用文章** を貼る
4. AIが `resume_context(slot_name="...")` で読み込み、作業を再開する

---

#### この画面でできること

- **保存用文章**: 今の作業をA2CRへ保存するためのコピー用文章。現在のSlot番号と `slot_name` の対応表も含みます
- **現在のスロット**: 保存中のSlot一覧。ローカルMVPでは最大 **3件**
- **ロード用文章**: Slotごとに表示される、新しい窓へ貼る再開用文章
- **Slot内容**: ローカルMVPでは確認用に展開表示できます。Web SaaS版では本文表示しない方針です
- **削除**: 不要なSlotを手動削除します
- **ライト**: ライトテーマとダークテーマを切り替えます
- **自動**: ONの場合、5分ごとに自動更新します
- **更新**: すぐに画面を再読み込みします

---

#### 表示される数字

- **累計保存回数**: `save_context` が成功した合計回数
- **累計ロード回数**: `load_context` / `resume_context` で読み込まれた合計回数
- **累計節約トークン**: 元の会話を丸ごと渡す場合と比べた概算の節約量
- **残り時間**: ローカルMVPでは保存から **30分** で自動削除。上書き保存で延長されます
""",
        "stat_saves": "累計保存回数",
        "stat_saves_help": "Claude が save_context を呼んだ合計回数",
        "stat_loads": "累計ロード回数",
        "stat_loads_help": "Claude が load_context を呼んだ合計回数",
        "stat_tokens": "累計節約トークン（概算）",
        "stat_tokens_help": "元の会話をそのまま渡す場合と比べた削減トークン数の合計",
        "slot_header": "現在のスロット（{n}/3 件使用中）",
        "no_slots": "保存されているスロットはありません。",
        "time_left": "残り",
        "minutes": "分",
        "model": "モデル",
        "size": "サイズ",
        "compressed": "圧縮後",
        "saved": "節約",
        "loads": "ロード",
        "loads_unit": "回",
        "delete": "削除",
        "delete_ok": "削除しました",
        "delete_fail": "削除失敗",
        "empty_slot": "空きSlot",
        "empty_slot_help": "保存するとここに表示されます。",
        "saved_at": "保存日時",
        "new_badge": "New",
        "save_prompt_label": "保存用文章（コピーしてAIに貼る）",
        "load_prompt_label": "ロード用文章（コピーして新しい窓に貼る）",
        "copy_prompt": "コピー",
        "copied_prompt": "コピーしました",
        "auto_reload_help": "5分ごとに自動更新",
        "auto_reload_label": "自動",
        "reload_now": "更新",
        "reload_now_help": "今すぐ更新",
        "theme_toggle_label": "ライト",
        "theme_toggle_help": "ONでライトテーマ、OFFでダークテーマ",
    },
    "en": {
        "server_on": "### 🟢 Running",
        "server_off": "### 🔴 Stopped",
        "usage_label": "📖 How to use",
        "usage_text": """
**A2CR** is a local MVP that temporarily saves AI work context and hands it off to a new conversation window.

---

#### Basic Flow

1. Copy the **Save prompt** above the Slot list into the current AI chat
2. The AI saves the current work with `save_context`. You can specify a destination by Slot number
3. In a new window, copy the target Slot's **Load prompt**
4. The AI runs `resume_context(slot_name="...")` and resumes the work

---

#### What This Screen Does

- **Save prompt**: Copyable text for asking the AI to save the current work. It also includes the current Slot number to `slot_name` map
- **Current slots**: Saved Slot list. The local MVP supports up to **3 slots**
- **Load prompt**: Per-Slot resume text to paste into a new AI window
- **Slot contents**: The local MVP can expand and show contents for checking. The Web SaaS version will not show saved content in the dashboard
- **Delete**: Manually remove an unneeded Slot
- **Light**: Switch between light and dark themes
- **Auto**: When enabled, reloads the screen every 5 minutes
- **Reload**: Reload the screen immediately

---

#### Metrics

- **Total Saves**: Successful `save_context` calls
- **Total Loads**: Successful `load_context` / `resume_context` reads
- **Total Tokens Saved**: Estimated token savings compared with passing the full conversation
- **Time left**: In the local MVP, Slots are auto-deleted **30 min** after saving. Overwriting a Slot extends it
""",
        "stat_saves": "Total Saves",
        "stat_saves_help": "Total number of times Claude called save_context",
        "stat_loads": "Total Loads",
        "stat_loads_help": "Total number of times Claude called load_context",
        "stat_tokens": "Total Tokens Saved (est.)",
        "stat_tokens_help": "Total reduction in tokens vs. passing the full conversation",
        "slot_header": "Current slots ({n}/3 in use)",
        "no_slots": "No slots are currently saved.",
        "time_left": "left",
        "minutes": "min",
        "model": "Model",
        "size": "Size",
        "compressed": "Compressed",
        "saved": "Saved",
        "loads": "Loads",
        "loads_unit": "",
        "delete": "Delete",
        "delete_ok": "Deleted successfully",
        "delete_fail": "Delete failed",
        "empty_slot": "Empty Slot",
        "empty_slot_help": "A saved context will appear here.",
        "saved_at": "Saved",
        "new_badge": "New",
        "save_prompt_label": "Save prompt (copy into AI chat)",
        "load_prompt_label": "Load prompt (copy into a new AI window)",
        "copy_prompt": "Copy",
        "copied_prompt": "Copied",
        "auto_reload_help": "Auto reload every 5 minutes",
        "auto_reload_label": "Auto",
        "reload_now": "Reload",
        "reload_now_help": "Reload now",
        "theme_toggle_label": "Light",
        "theme_toggle_help": "On for light theme, off for dark theme",
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _load_stats() -> Stats | None:
    with Session(get_engine()) as session:
        return session.get(Stats, 1)


def _stat_card(label: str, value: str | int, help_text: str) -> str:
    return (
        '<div class="stat-card">'
        f'<div class="stat-label">{html.escape(label)}'
        f'<span class="stat-help" title="{html.escape(help_text)}">?</span></div>'
        f'<div class="stat-value">{html.escape(str(value))}</div>'
        "</div>"
    )


def _copy_prompt_box(text: str, copy_label: str, copied_label: str) -> None:
    escaped_text = html.escape(text)
    text_json = json.dumps(text, ensure_ascii=False)
    copy_json = json.dumps(copy_label, ensure_ascii=False)
    copied_json = json.dumps(copied_label, ensure_ascii=False)
    estimated_lines = text.count("\n") + max(1, len(text) // 58)
    height = min(260, max(112, 68 + estimated_lines * 22))
    components.html(
        f"""
<div class="copy-card">
  <button class="copy-button" type="button">{html.escape(copy_label)}</button>
  <pre class="copy-text">{escaped_text}</pre>
</div>
<script>
const text = {text_json};
const copyLabel = {copy_json};
const copiedLabel = {copied_json};
const button = document.querySelector(".copy-button");

function fallbackCopy(value) {{
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}}

button.addEventListener("click", async () => {{
  try {{
    if (navigator.clipboard && window.isSecureContext) {{
      await navigator.clipboard.writeText(text);
    }} else {{
      fallbackCopy(text);
    }}
    button.textContent = copiedLabel;
    window.setTimeout(() => {{ button.textContent = copyLabel; }}, 1400);
  }} catch (error) {{
    fallbackCopy(text);
    button.textContent = copiedLabel;
    window.setTimeout(() => {{ button.textContent = copyLabel; }}, 1400);
  }}
}});
</script>
<style>
html, body {{
  margin: 0;
  padding: 0;
  background: transparent;
}}
.copy-card {{
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  margin: 0;
  padding: 0.65rem 0.75rem 0.75rem;
  border: 1px solid #242b38;
  border-radius: 8px;
  background: #171b24;
  color: #f8fafc;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}}
.copy-button {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 1.9rem;
  margin: 0 0 0.55rem;
  padding: 0.25rem 0.65rem;
  border: 1px solid #64748b;
  border-radius: 6px;
  background: #f8fafc;
  color: #0f172a;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}}
.copy-button:hover {{
  border-color: #38bdf8;
  color: #075985;
}}
.copy-text {{
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  color: #f8fafc;
  font-size: 0.9rem;
  line-height: 1.45;
}}
</style>
""",
        height=height,
        scrolling=False,
    )


def _stats_band(stats: Stats, translations: dict) -> str:
    return (
        '<div class="stats-band stats-side">'
        + _stat_card(translations["stat_saves"], stats.total_saves, translations["stat_saves_help"])
        + _stat_card(translations["stat_loads"], stats.total_loads, translations["stat_loads_help"])
        + _stat_card(translations["stat_tokens"], f"{stats.total_tokens_saved:,}", translations["stat_tokens_help"])
        + "</div>"
    )


def _load_slots() -> list[dict]:
    now = _now()
    with Session(get_engine()) as session:
        slot_number_column = getattr(Context, "slot_number", None)
        stmt = select(Context).where(Context.expires_at > now)
        if slot_number_column is None:
            stmt = stmt.order_by(Context.updated_at.desc())
        else:
            stmt = stmt.order_by(slot_number_column.asc(), Context.updated_at.desc())

        rows = session.execute(stmt).scalars().all()
        slots = []
        for fallback_number, r in enumerate(rows, start=1):
            slot_number = getattr(r, "slot_number", None)
            if slot_number is None and fallback_number <= 3:
                slot_number = fallback_number
            slots.append(
                {
                "slot_name": r.slot_name,
                "slot_number": slot_number,
                "size_bytes": r.size_bytes,
                "expires_at": r.expires_at,
                "updated_at": r.updated_at,
                "compressed_tokens": r.compressed_tokens,
                "original_tokens": r.original_tokens,
                "model_source": r.model_source,
                "load_count": r.load_count,
                "content_encrypted": r.content,
                }
            )
        return slots


def _decrypt_content(encrypted: str) -> dict | None:
    try:
        return json.loads(decrypt(encrypted))
    except Exception:
        return None


def _slot_save_map(slots: list[dict], lang: str) -> str:
    slot_by_number = {
        slot["slot_number"]: slot
        for slot in slots
        if slot.get("slot_number") is not None
    }
    lines = []
    for index in range(3):
        slot_number = index + 1
        slot = slot_by_number.get(slot_number)
        if slot is None:
            if lang == "ja":
                lines.append(f'Slot {slot_number}: slot_number={slot_number}, slot_name="slot-{slot_number}"（空きSlot）')
            else:
                lines.append(f'Slot {slot_number}: slot_number={slot_number}, slot_name="slot-{slot_number}" (empty Slot)')
        else:
            lines.append(f'Slot {slot_number}: slot_number={slot_number}, slot_name="{slot["slot_name"]}"')
    return "\n".join(lines)


def _save_prompt(lang: str, slots: list[dict]) -> str:
    slot_map = _slot_save_map(slots, lang)
    if lang == "ja":
        return (
            f"A2CR service: {SERVICE_URL} "
            "A2CR MCPの save_context を使って、現在の作業を引き継ぎ用に保存してください。"
            "保存先Slot番号を指定された場合は、下記対応表の slot_number と slot_name を使って保存してください。\n"
            f"{slot_map}\n"
            "保存後、新しい窓への再開用メッセージも表示してください。"
        )
    return (
        f"A2CR service: {SERVICE_URL} "
        "Use A2CR MCP save_context to save the current work as handoff context. "
        "If a destination Slot number is specified, use the matching slot_number and slot_name below.\n"
        f"{slot_map}\n"
        "After saving, show the resume prompt for a new AI window."
    )


def _load_prompt(slot_name: str, slot_number: int | None, lang: str) -> str:
    slot_name_call = f'resume_context(slot_name="{slot_name}")'
    ja_slot_number_hint = (
        f"Slot番号対応済みなら resume_context(slot_number={slot_number}) でも読み込めます。\n"
        if slot_number is not None
        else ""
    )
    en_slot_number_hint = (
        f"If your MCP tool supports fixed Slot numbers, resume_context(slot_number={slot_number}) also works.\n"
        if slot_number is not None
        else ""
    )
    if lang == "ja":
        return (
            f"A2CR service: {SERVICE_URL}\n"
            "A2CR MCPツールを使ってください。HTTP APIを直接推測して呼び出さないでください。\n"
            "まず次を実行してください:\n"
            f"{slot_name_call}\n"
            f"{ja_slot_number_hint}"
            "A2CRから引き継ぎ文脈を読み込んでください。\n"
            "読み込み後は、作業に必要なプロジェクトファイルを通常通り参照して構いません。\n"
            "回答はこのメッセージの言語に合わせてください。"
        )
    return (
        f"A2CR service: {SERVICE_URL}\n"
        "Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.\n"
        "First run:\n"
        f"{slot_name_call}\n"
        f"{en_slot_number_hint}"
        "Load the handoff context from A2CR.\n"
        "After loading, you may read the project files needed for the actual work.\n"
        "Answer in the language of this message."
    )


def _minutes_left(expires_at: datetime) -> float:
    return max(0.0, (expires_at - _now()).total_seconds() / 60)


def _format_saved_at(saved_at: datetime | None, lang: str) -> str:
    if saved_at is None:
        return "—"
    if saved_at.tzinfo is None:
        saved_at = saved_at.replace(tzinfo=timezone.utc)
    local_saved_at = saved_at.astimezone()
    if lang == "ja":
        return local_saved_at.strftime("%Y/%m/%d %H:%M")
    return local_saved_at.strftime("%Y-%m-%d %H:%M")


def _is_latest_slot(slot: dict, latest_updated_at: datetime | None) -> bool:
    return latest_updated_at is not None and slot.get("updated_at") == latest_updated_at


def _slot_card_heading(index: int, slot: dict | None, latest_updated_at: datetime | None, translations: dict, lang: str) -> str:
    title = f"Slot {index}"
    if slot is None:
        return f'<div class="slot-card-heading"><span class="slot-card-title">{title}</span></div>'

    new_badge = ""
    if _is_latest_slot(slot, latest_updated_at):
        new_badge = f'<span class="slot-new-badge">{html.escape(translations["new_badge"])}</span>'

    saved_at = _format_saved_at(slot.get("updated_at"), lang)
    return (
        '<div class="slot-card-heading">'
        f'<span class="slot-card-title">{title}</span>'
        '<span class="slot-card-meta">'
        f'{new_badge}<span>{html.escape(translations["saved_at"])}: {html.escape(saved_at)}</span>'
        "</span>"
        "</div>"
    )


def _load_dashboard_settings() -> dict:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_dashboard_settings() -> None:
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(
            json.dumps(
                {
                    "lang": st.session_state.lang,
                    "light_theme": bool(st.session_state.light_theme),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def _slot_label(slot_name: str, minutes: float, time_color: str, lang: str, light_theme: bool) -> str:
    suffix = f"{minutes:.0f} {T[lang]['minutes']} {T[lang]['time_left']}"
    if light_theme:
        return f"**{slot_name}**  —  :red[{suffix}]"
    return f"**{slot_name}**  —  :{time_color}[{suffix}]"


def _theme_css(light_theme: bool) -> str:
    if light_theme:
        return """
<style>
  .stApp,
  [data-testid="stAppViewContainer"],
  [data-testid="stHeader"] {
    background: #f8f2e8 !important;
    color: #0f172a !important;
  }
  .block-container,
  [data-testid="stMarkdownContainer"],
  [data-testid="stMarkdownContainer"] * {
    color: #0f172a !important;
  }
  [data-testid="stMarkdownContainer"] code {
    background: #e2e8f0 !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 4px !important;
    padding: 0.08rem 0.28rem !important;
  }
  .app-title,
  .app-status {
    color: #0f172a !important;
  }
  .stats-band {
    background: #e7f6f2 !important;
    border-color: #5dbfb4 !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8) !important;
  }
  .stat-label,
  .stat-value {
    color: #0f172a !important;
  }
  .stat-help {
    border-color: rgba(15, 23, 42, 0.45) !important;
    color: rgba(15, 23, 42, 0.7) !important;
  }
  div[data-testid="stCodeBlock"],
  div[data-testid="stCodeBlock"] > div {
    background: transparent !important;
  }
  div[data-testid="stCodeBlock"] pre {
    background: #18202b !important;
    border: 1px solid #334155 !important;
    color: #0f172a !important;
  }
  div[data-testid="stCodeBlock"] code {
    color: #f8fafc !important;
  }
  div[class*="st-key-slot_panel_"] {
    background: #fbf3e4 !important;
    border-color: #dec9a8 !important;
    box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04) !important;
  }
  .slot-card-meta {
    color: rgba(15, 23, 42, 0.72) !important;
  }
  .slot-new-badge {
    background: #dc2626 !important;
    color: #ffffff !important;
  }
  div[data-testid="stExpander"] details {
    background: #ffffff !important;
    border-color: #cbd5e1 !important;
  }
  div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: #ffffff !important;
  }
  div[data-testid="stExpander"] summary,
  div[data-testid="stExpander"] summary * {
    color: #0f172a !important;
  }
  div[data-testid="stSelectbox"] {
    max-width: 150px !important;
  }
  div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: #ffffff !important;
    border: 1px solid #94a3b8 !important;
    border-radius: 8px !important;
  }
  div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
  div[data-testid="stSelectbox"] div[data-baseweb="select"] input,
  div[data-testid="stSelectbox"] div[data-baseweb="select"] div,
  div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
    background: #ffffff !important;
    color: #0f172a !important;
  }
  div[data-testid="stSelectbox"] div[data-baseweb="select"] svg {
    fill: #334155 !important;
    color: #334155 !important;
  }
  div[data-baseweb="popover"],
  div[data-baseweb="popover"] ul,
  div[data-baseweb="popover"] li,
  div[data-baseweb="popover"] div {
    background: #ffffff !important;
    color: #0f172a !important;
  }
  div[data-baseweb="popover"] li:hover {
    background: #e0f2fe !important;
  }
  div[data-baseweb="tooltip"],
  div[data-baseweb="tooltip"] div,
  div[data-baseweb="tooltip"] p,
  div[data-baseweb="tooltip"] span {
    background: #111827 !important;
    color: #f8fafc !important;
  }
  div[data-baseweb="tooltip"] {
    border: 1px solid #475569 !important;
    border-radius: 8px !important;
  }
  div[data-testid="stButton"] button {
    background: #ffffff !important;
    border: 1px solid #94a3b8 !important;
    color: #0f172a !important;
  }
  div[data-testid="stButton"] button:hover {
    border-color: #2563eb !important;
    color: #1d4ed8 !important;
  }
  div[data-testid="stToggle"] label,
  div[data-testid="stToggle"] label * {
    color: #0f172a !important;
    opacity: 1 !important;
  }
  div[data-testid="stCheckbox"] label,
  div[data-testid="stCheckbox"] label * {
    color: #0f172a !important;
    opacity: 1 !important;
  }
  div[data-testid="stCheckbox"] input {
    opacity: 1 !important;
  }
  div[data-testid="stToggle"] label {
    white-space: nowrap !important;
  }
  div[data-testid="stCheckbox"] label {
    white-space: nowrap !important;
  }
  div[data-testid="stToggle"] svg,
  div[data-testid="stTooltipIcon"] svg,
  [data-testid="stTooltipIcon"],
  [data-testid="stTooltipIcon"] * {
    color: #334155 !important;
    fill: #334155 !important;
    opacity: 1 !important;
  }
  div[data-testid="stToggle"] [role="switch"] {
    background: #cbd5e1 !important;
    border: 1px solid #64748b !important;
    opacity: 1 !important;
  }
  div[data-testid="stToggle"] [role="switch"][aria-checked="true"] {
    background: #ef4444 !important;
    border-color: #ef4444 !important;
  }
  div[data-testid="stToggle"] [role="switch"] * {
    opacity: 1 !important;
  }
  div[data-testid="stAlert"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
  }
  hr {
    border-color: #cbd5e1 !important;
  }
</style>
"""
    return """
<style>
  .stats-band {
    background: #10201f !important;
    border-color: rgba(45, 212, 191, 0.34) !important;
  }
  .stat-label {
    color: rgba(255, 255, 255, 0.88) !important;
  }
  .stat-value {
    color: #ffffff !important;
  }
</style>
"""


# ─── Available languages (add entries here to support more) ──────────
LANGUAGES = {
    "ja": "🇯🇵 日本語",
    "en": "🇬🇧 English",
}

# ─── Server status ────────────────────────────────────────────────────
def _check_server() -> bool:
    try:
        r = requests.get(f"{API_BASE}/v1/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False

# ─── Session state defaults ───────────────────────────────────────────
dashboard_settings = _load_dashboard_settings()
if "lang" not in st.session_state:
    saved_lang = dashboard_settings.get("lang", "ja")
    st.session_state.lang = saved_lang if saved_lang in LANGUAGES else "ja"
if "auto_reload" not in st.session_state:
    st.session_state.auto_reload = True
if "light_theme" not in st.session_state:
    st.session_state.light_theme = bool(dashboard_settings.get("light_theme", False))

st.markdown(_theme_css(st.session_state.light_theme), unsafe_allow_html=True)

# ─── Conditional auto-refresh ─────────────────────────────────────────
if st.session_state.auto_reload:
    st.markdown(
        f'<meta http-equiv="refresh" content="{AUTO_RELOAD_SECONDS}">',
        unsafe_allow_html=True,
    )

t = T[st.session_state.lang]

# ─── Header ───────────────────────────────────────────────────────────
server_ok = _check_server()
status_html = t["server_on"].replace("### ", "") if server_ok else t["server_off"].replace("### ", "")

left_col, spacer_col, ctrl_col = st.columns([3.4, 1.4, 2.7], gap="small", vertical_alignment="center")
left_col.markdown(
    "<div class='app-header'>"
    "<span class='app-title'>A2CR</span>"
    f"<span class='app-status'>{status_html}</span>"
    f"</div>",
    unsafe_allow_html=True,
)
spacer_col.markdown("<div class='header-spacer-anchor'></div>", unsafe_allow_html=True)
with ctrl_col:
    with st.container(key="header_controls"):
        st.markdown("<div class='header-controls-anchor'></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:0.65rem'></div>", unsafe_allow_html=True)
        lang_c, theme_c, auto_c, reload_c = st.columns(
            [1.5, 1.0, 0.9, 0.85],
            gap="small",
            vertical_alignment="center",
        )
        lang_c.selectbox(
            "Language",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: LANGUAGES[x],
        key="lang",
        label_visibility="collapsed",
        on_change=_save_dashboard_settings,
    )
        theme_c.checkbox(
            t["theme_toggle_label"],
            key="light_theme",
            help=t["theme_toggle_help"],
            on_change=_save_dashboard_settings,
        )
        auto_c.checkbox(
            t["auto_reload_label"],
            key="auto_reload",
            help=t["auto_reload_help"],
        )
        if reload_c.button(t["reload_now"], help=t["reload_now_help"]):
            st.rerun()

with st.expander(t["usage_label"], expanded=False):
    st.markdown(t["usage_text"])


# ─── Main content ─────────────────────────────────────────────────────
stats = _load_stats()
slots = _load_slots()
slot_by_number = {
    slot["slot_number"]: slot
    for slot in slots
    if slot.get("slot_number") is not None
}
latest_updated_at = max((slot["updated_at"] for slot in slots if slot["updated_at"] is not None), default=None)
main_col, stats_col = st.columns([3.25, 1.05], gap="large")

with main_col:
    st.markdown(f"**{t['save_prompt_label']}**")
    _copy_prompt_box(_save_prompt(st.session_state.lang, slots), t["copy_prompt"], t["copied_prompt"])
    st.divider()

    with st.container(height=SLOT_SCROLL_HEIGHT, border=False):
        st.subheader(t["slot_header"].format(n=len(slots)))

        slot_columns = st.columns(3, gap="medium")
        for index in range(3):
            slot_number = index + 1
            slot = slot_by_number.get(slot_number)
            with slot_columns[index]:
                with st.container(key=f"slot_panel_{slot_number}"):
                    st.markdown(
                        _slot_card_heading(slot_number, slot, latest_updated_at, t, st.session_state.lang),
                        unsafe_allow_html=True,
                    )

                    if slot is None:
                        st.markdown(f"**{t['empty_slot']}**")
                        st.caption(t["empty_slot_help"])
                        continue

                    minutes = _minutes_left(slot["expires_at"])
                    time_color = "orange" if minutes < 10 else "green"
                    saved = (
                        (slot["original_tokens"] - slot["compressed_tokens"])
                        if slot["original_tokens"] is not None
                        else None
                    )
                    expander_label = _slot_label(
                        slot["slot_name"],
                        minutes,
                        time_color,
                        st.session_state.lang,
                        st.session_state.light_theme,
                    )

                    with st.expander(expander_label):
                        st.markdown(f"**{t['model']}:** `{slot['model_source'] or '—'}`")
                        st.markdown(f"**{t['size']}:** {slot['size_bytes']:,} B")
                        st.markdown(f"**{t['compressed']}:** {slot['compressed_tokens']:,} tok")
                        if saved is not None:
                            st.markdown(f"**{t['saved']}:** {saved:,} tok")
                        else:
                            st.markdown(f"**{t['saved']}:** —")
                        st.markdown(f"**{t['loads']}:** {slot['load_count']} {t['loads_unit']}")

                        content = _decrypt_content(slot["content_encrypted"])
                        if content:
                            st.markdown("**goal:** " + content.get("goal", ""))
                            st.markdown("**current_state:** " + content.get("current_state", ""))
                            st.markdown("**next_action:** " + content.get("next_action", ""))
                            st.json(content)

                        if st.button(t["delete"], key=f"del-{slot['slot_name']}"):
                            r = requests.delete(
                                f"{API_BASE}/v1/context/{slot['slot_name']}", headers=HEADERS, timeout=5
                            )
                            if r.ok:
                                st.success(t["delete_ok"])
                                st.rerun()
                            else:
                                st.error(f"{t['delete_fail']}: {r.text}")

                    st.markdown(f"**{t['load_prompt_label']}**")
                    _copy_prompt_box(
                        _load_prompt(slot["slot_name"], slot.get("slot_number"), st.session_state.lang),
                        t["copy_prompt"],
                        t["copied_prompt"],
                    )

with stats_col:
    if stats:
        st.markdown(_stats_band(stats, t), unsafe_allow_html=True)

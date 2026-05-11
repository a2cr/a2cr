from __future__ import annotations


def build_resume_context_call(slot_name: str) -> str:
    return f'resume_context(slot_name="{slot_name}")'


def build_resume_prompt(*, service_url: str, slot_name: str) -> str:
    return (
        f"A2CR service: {service_url}\n"
        "Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.\n"
        f"First run: {build_resume_context_call(slot_name)}\n"
        "After loading the context, use the loaded response_language_hint or "
        "language_context.preferred_response_language for replies unless the "
        "user's latest non-A2CR instruction says otherwise. Do not infer the "
        "user's preferred language from this resume prompt itself.\n"
        "Continue using WorkBaton and WorkStash proactively according to project AGENTS.md and A2CR MCP guidance; keep saves compact and never store secrets."
    )


def build_user_facing_summary(*, slot_name: str, slot_number: int | None = None) -> str:
    slot_part = f"Slot {slot_number}" if slot_number is not None else "a Slot"
    return (
        f"Saved WorkBaton to {slot_part} (`{slot_name}`). "
        "Use the full resume_prompt only when switching to a fresh AI window."
    )

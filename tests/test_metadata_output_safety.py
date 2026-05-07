from pathlib import Path

import pytest
from pydantic import ValidationError

from models.schemas import SaveRequest, WebContextSaveRequest, WorkThreadResultSaveRequest


CONTENT = {
    "goal": "metadata safety",
    "current_state": "testing",
    "next_action": "assert",
}


def encrypted(label: str = "ciphertext") -> dict:
    return {
        "version": 1,
        "alg": "Fernet",
        "nonce": "embedded",
        "ciphertext": label,
        "key_wrap": {"type": "local-key", "kid": "test"},
    }


@pytest.mark.parametrize("slot_name", ["_safe", "slot-a", "slot_1"])
def test_slot_name_accepts_safe_metadata_values(slot_name):
    SaveRequest(slot_name=slot_name, encrypted_content=encrypted())
    WebContextSaveRequest(slot_name=slot_name, encrypted_content=encrypted())
    WorkThreadResultSaveRequest(slot_name=slot_name, content=CONTENT)


@pytest.mark.parametrize(
    "slot_name",
    [
        "<script>alert('x')</script>",
        "=HYPERLINK",
        "+SUM",
        "-cmd",
        "@HYPERLINK",
    ],
)
def test_slot_name_rejects_xss_and_csv_formula_prefixes(slot_name):
    with pytest.raises(ValidationError):
        SaveRequest(slot_name=slot_name, encrypted_content=encrypted())
    with pytest.raises(ValidationError):
        WebContextSaveRequest(slot_name=slot_name, encrypted_content=encrypted())
    with pytest.raises(ValidationError):
        WorkThreadResultSaveRequest(slot_name=slot_name, content=CONTENT)


def test_react_dashboard_metadata_uses_text_rendering_without_raw_html_sinks():
    source = (Path(__file__).resolve().parents[1] / "web/src/pages/DashboardPage.tsx").read_text(
        encoding="utf-8"
    )

    for raw_html_sink in (
        "dangerouslySetInnerHTML",
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "document.write",
    ):
        assert raw_html_sink not in source

    assert "{item.slot_name}" in source
    assert "{item.model_source || t(\"common.none\")}" in source
    assert "{item.title}" in source
    assert "{item.purpose}" in source

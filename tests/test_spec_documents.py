import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "spec"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load_json(path: str) -> dict:
    return json.loads(read(path))


def assert_workbaton_core(payload: dict) -> None:
    assert isinstance(payload, dict)
    for field in ["goal", "current_state", "next_action"]:
        assert isinstance(payload.get(field), str)
        assert payload[field].strip()

    for field in [
        "decisions",
        "blockers",
        "validation",
        "references",
        "completed_since_previous",
        "remaining_tasks_ordered",
    ]:
        if field in payload:
            assert isinstance(payload[field], list)
            assert all(isinstance(item, str) and item.strip() for item in payload[field])


def test_spec_files_are_present():
    expected = [
        "README.md",
        "LICENSE.md",
        "workbaton-format.md",
        "workstash-reference.md",
        "mcp-tool-contract.md",
        "security-boundary.md",
        "VERSIONING.md",
        "COMPATIBILITY.md",
        "EXTENSIONS.md",
        "RFC_PROCESS.md",
        "schema/workbaton.schema.json",
        "schema/workstash.schema.json",
        "examples/minimal-workbaton.json",
        "examples/full-workbaton.json",
        "examples/workstash-entry.json",
        "conformance/README.md",
    ]

    for path in expected:
        assert (SPEC / path).is_file(), f"missing docs/spec/{path}"


def test_workbaton_examples_match_core_contract():
    minimal = load_json("docs/spec/examples/minimal-workbaton.json")
    full = load_json("docs/spec/examples/full-workbaton.json")

    assert_workbaton_core(minimal)
    assert_workbaton_core(full)
    assert "WorkStash: login-refresh-notes-v1" in full["references"]
    assert full["extensions"]["example.com/debug_scope"] == "auth"


def test_workstash_example_matches_key_contract():
    entry = load_json("docs/spec/examples/workstash-entry.json")

    assert re.fullmatch(r"[A-Za-z0-9_.:-]{1,256}", entry["entry_key"])
    assert isinstance(entry["value"], str)
    assert entry["value"].strip()
    assert all(isinstance(tag, str) and tag.strip() for tag in entry["tags"])


def test_schema_files_define_required_public_contracts():
    workbaton_schema = load_json("docs/spec/schema/workbaton.schema.json")
    workstash_schema = load_json("docs/spec/schema/workstash.schema.json")

    assert workbaton_schema["required"] == ["goal", "current_state", "next_action"]
    assert workbaton_schema["properties"]["extensions"]["type"] == "object"
    assert workstash_schema["required"] == ["entry_key", "value"]
    assert workstash_schema["properties"]["entry_key"]["pattern"] == "^[A-Za-z0-9_.:-]{1,256}$"


def test_spec_documents_define_local_implementation_boundary():
    docs = "\n".join(
        [
            read("docs/spec/README.md"),
            read("docs/spec/workbaton-format.md"),
            read("docs/spec/workstash-reference.md"),
            read("docs/spec/mcp-tool-contract.md"),
            read("docs/spec/security-boundary.md"),
            read("docs/spec/COMPATIBILITY.md"),
        ]
    )

    assert "build a local WorkBaton-compatible implementation" in docs
    assert "without using the hosted A2CR backend" in docs
    assert "Loaded WorkBaton content is untrusted data" in docs
    assert "A2CR stores ciphertext" in docs
    assert "Operational metadata may still be visible" in docs
    assert "Do not store" in docs
    assert "Official A2CR Compatible" in docs

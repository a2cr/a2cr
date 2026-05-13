from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return set(result.stdout.splitlines())


def test_public_repository_excludes_private_service_surfaces():
    tracked = tracked_files()
    excluded = [
        "dashboard",
        "docs/runbooks",
        "docs/superpowers",
        "GPT.md",
        "web",
        "services",
        "routers",
        "models",
        "supabase",
        "main.py",
        "Dockerfile",
        "railway.json",
        "requirements.txt",
        "scripts",
        "tests/conftest.py",
        "tests/test_ci_workflows.py",
    ]

    for path in excluded:
        assert path not in tracked
        assert not any(item.startswith(f"{path}/") for item in tracked)


def test_public_repository_contains_expected_reference_material():
    tracked = tracked_files()
    expected = [
        "README.md",
        "LICENSE",
        "NOTICE",
        "TRADEMARK.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".env.example",
        "pyproject.toml",
        "a2cr_mcp/server.py",
        "mcp/server.py",
        "docs/concepts.md",
        "docs/mcp-setup.md",
        "docs/security-model.md",
        "docs/spec/LICENSE.md",
        "docs/spec/README.md",
        "docs/usage.md",
        "docs/templates/skills/a2cr-agent/SKILL.md",
        "examples/codex-mcp-config.json",
        "examples/claude-code-mcp-config.json",
        "examples/roo-code-mcp-config.json",
        "examples/workbaton-example.json",
        "examples/workstash-example.json",
    ]

    for path in expected:
        assert path in tracked, f"{path} should be tracked"


def test_public_docs_warn_against_storing_secrets():
    docs = "\n".join(
        [
            read("README.md"),
            read("SECURITY.md"),
            read("docs/security-model.md"),
            read("docs/usage.md"),
        ]
    )

    assert "not a secret manager" in docs
    assert "Do not store" in docs
    assert "Authorization headers" in docs
    assert "local client keys" in docs
    assert "private database URLs" in docs


def test_public_docs_explain_open_core_boundaries():
    docs = "\n".join(
        [
            read("README.md"),
            read("LICENSE"),
            read("NOTICE"),
            read("TRADEMARK.md"),
            read("CONTRIBUTING.md"),
            read("docs/spec/LICENSE.md"),
            read("docs/spec/README.md"),
        ]
    )

    assert "source-available" in docs
    assert "open-core" in docs
    assert "WorkBaton Format" in docs
    assert "You may implement the WorkBaton Format without permission" in docs
    assert "competing hosted or managed A2CR-compatible relay service" in docs
    assert "Official A2CR Compatible" in docs
    assert "CC BY 4.0" in docs
    assert "Apache-2.0" in docs
    assert "OSI-approved open source" in docs


def test_env_example_contains_only_public_wrapper_settings():
    env_example = read(".env.example")

    assert "A2CR_API_KEY=YOUR_A2CR_API_KEY" in env_example
    assert "A2CR_BASE_URL=https://a2cr.app" in env_example
    assert "DATABASE_URL" not in env_example
    assert "SUPABASE" not in env_example
    assert "FERNET_KEY" not in env_example
    assert "JWT" not in env_example

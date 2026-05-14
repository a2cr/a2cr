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
        "PUBLIC_RELEASE.md",
        "SECURITY_CHECKLIST.md",
        "TRADEMARK.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".env.example",
        ".github/dependabot.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/pull_request_template.md",
        ".github/workflows/ci.yml",
        ".github/workflows/codeql.yml",
        ".github/workflows/dependency-review.yml",
        ".github/workflows/publish-mcp-registry.yml",
        "server.json",
        "pyproject.toml",
        "a2cr_mcp/server.py",
        "mcp/server.py",
        "docs/concepts.md",
        "docs/mcp-setup.md",
        "docs/mcp-registry-publishing.md",
        "docs/official-distribution-roadmap.md",
        "docs/security-model.md",
        "docs/spec/LICENSE.md",
        "docs/spec/README.md",
        "docs/spec/workbaton-format.md",
        "docs/spec/workstash-reference.md",
        "docs/spec/mcp-tool-contract.md",
        "docs/spec/security-boundary.md",
        "docs/spec/VERSIONING.md",
        "docs/spec/COMPATIBILITY.md",
        "docs/spec/EXTENSIONS.md",
        "docs/spec/RFC_PROCESS.md",
        "docs/spec/schema/workbaton.schema.json",
        "docs/spec/schema/workstash.schema.json",
        "docs/spec/examples/minimal-workbaton.json",
        "docs/spec/examples/full-workbaton.json",
        "docs/spec/examples/workstash-entry.json",
        "docs/spec/conformance/README.md",
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
            read("SECURITY_CHECKLIST.md"),
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
            read("PUBLIC_RELEASE.md"),
            read("SECURITY_CHECKLIST.md"),
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


def test_mcp_registry_metadata_matches_package_readme():
    import json

    server = json.loads(read("server.json"))
    readme = read("README.md")

    assert server["$schema"] == "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"
    assert server["name"] == "io.github.a2cr/a2cr-mcp"
    assert server["version"] == "0.1.5"
    assert "<!-- mcp-name: io.github.a2cr/a2cr-mcp -->" in readme

    package = server["packages"][0]
    assert package["registryType"] == "pypi"
    assert package["identifier"] == "a2cr-mcp"
    assert package["version"] == server["version"]
    assert package["transport"]["type"] == "stdio"

    api_key_env = next(
        item for item in package["environmentVariables"]
        if item["name"] == "A2CR_API_KEY"
    )
    assert api_key_env["isRequired"] is True
    assert api_key_env["isSecret"] is True


def test_official_distribution_roadmap_keeps_remote_boundaries_explicit():
    docs = "\n".join(
        [
            read("docs/mcp-registry-publishing.md"),
            read("docs/official-distribution-roadmap.md"),
            read("SECURITY_CHECKLIST.md"),
            read("PUBLIC_RELEASE.md"),
        ]
    )

    assert "io.github.a2cr/a2cr-mcp" in docs
    assert "Claude Desktop Extension" in docs
    assert "MCPB" in docs
    assert "Apps SDK" in docs
    assert "remote MCP" in docs
    assert "plaintext" in docs
    assert "local encryption" in docs
    assert "raw PyPI stdio package directly" in docs


def test_public_docs_define_security_responsibility_boundary():
    docs = "\n".join(
        [
            read("README.md"),
            read("SECURITY.md"),
            read("SECURITY_CHECKLIST.md"),
            read("docs/security-model.md"),
            read("docs/spec/security-boundary.md"),
            read(".github/pull_request_template.md"),
            read(".github/ISSUE_TEMPLATE/bug_report.yml"),
        ]
    )

    assert "Responsibility Boundary" in docs
    assert "restored context as untrusted" in docs
    assert "WorkBaton is work state, not an authority" in docs
    assert "Do not include secrets" in docs
    assert "GitHub private vulnerability reporting" in docs
    assert "Dependabot alerts" in docs
    assert "secret scanning" in docs


def test_env_example_contains_only_public_wrapper_settings():
    env_example = read(".env.example")

    assert "A2CR_API_KEY=YOUR_A2CR_API_KEY" in env_example
    assert "A2CR_BASE_URL=https://a2cr.app" in env_example
    assert "DATABASE_URL" not in env_example
    assert "SUPABASE" not in env_example
    assert "FERNET_KEY" not in env_example
    assert "JWT" not in env_example

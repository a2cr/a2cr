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
        "README-ja.md",
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
        "glama.json",
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
    assert server["version"] == "0.1.6"
    assert "<!-- mcp-name: io.github.a2cr/a2cr-mcp -->" in readme
    assert "https://registry.modelcontextprotocol.io/v0.1/servers/io.github.a2cr%2Fa2cr-mcp/versions/latest" in readme

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


def test_public_mcp_setup_examples_match_registry_environment():
    import json

    server = json.loads(read("server.json"))
    package = server["packages"][0]
    registry_env_names = {
        item["name"]
        for item in package["environmentVariables"]
    }

    docs = "\n".join(
        [
            read("README.md"),
            read("docs/mcp-setup.md"),
            read("docs/usage.md"),
            read("examples/codex-mcp-config.json"),
            read("examples/claude-code-mcp-config.json"),
        ]
    )

    assert "A2CR_API_KEY" in registry_env_names
    assert "A2CR_BASE_URL" in registry_env_names
    assert "A2CR_SERVICE_URL" not in registry_env_names
    assert "A2CR_SERVICE_URL" not in docs


def test_public_docs_keep_plan_limits_out_of_github_docs():
    import re

    docs = "\n".join(
        [
            read("README.md"),
            read("docs/mcp-setup.md"),
            read("docs/usage.md"),
            read("docs/spec/workstash-reference.md"),
            read("docs/templates/skills/a2cr-agent/SKILL.md"),
        ]
    )

    assert "get_account_limits" in docs
    assert re.search(r"\b\d+\s*KB\b", docs) is None
    assert re.search(r"\b\d+\s+days\b", docs, flags=re.IGNORECASE) is None
    assert re.search(r"\b(Free|Pro)\s+has\b", docs) is None


def test_readme_is_cleanly_separated_for_public_technical_docs():
    readme = read("README.md")
    readme_ja = read("README-ja.md")

    for marker in ["邵ｺ", "隴", "郢", "縺", "繝", "譌", "繧", "\ufffd"]:
        assert marker not in readme
        assert marker not in readme_ja

    assert "A2CR is an MCP server for AI agent handoffs" in readme
    assert "Long AI work usually breaks at the handoff" in readme
    assert "In this repository, an AI window means one active chat/session" in readme
    assert '"goal": "Fix the failing login test"' in readme
    assert "[Japanese overview](README-ja.md)" in readme
    assert readme.index("## Quickstart") < readme.index("## Why A2CR Exists")
    assert readme.index("## Quickstart") < readme.index("## Security Boundary")

    assert "A2CR 日本語概要" in readme_ja
    assert "このGitHubリポジトリは公開技術資料" in readme_ja
    assert "WorkThreads" in readme_ja


def test_package_metadata_supports_discovery_without_shipping_large_assets():
    pyproject = read("pyproject.toml")
    manifest = read("MANIFEST.in")

    for term in [
        "mcp-server",
        "model-context-protocol",
        "context-handoff",
        "agent-memory",
        "codex",
        "claude-code",
        "MCP Registry",
        "Source",
        "Issues",
    ]:
        assert term in pyproject

    assert "recursive-include docs *.md *.json" in manifest
    assert "*.png" not in manifest
    assert "*.gif" not in manifest


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
    assert "mcp-publisher validate server.json" in docs
    assert "publish server.json --dry-run" not in docs
    assert "P1 completion is the service-start line" in docs
    assert "A2CR public preview is live" in docs
    assert "Promotion starts after P1" in docs
    assert "development can continue in parallel" in docs
    assert "not a blocker for P1" in docs


def test_official_distribution_roadmap_keeps_service_operations_private():
    roadmap = read("docs/official-distribution-roadmap.md")

    assert "The public repository may describe WorkThreads" in roadmap
    assert "coordination concept" in roadmap
    assert "service operations belong in private" in roadmap
    assert "planning until they are intentionally published" in roadmap
    assert "private release planning" in roadmap

    for phrase in [
        "dashboard visibility",
        "support/debug runbooks",
        "reviewer test account",
        "rate limits and abuse controls",
        "hosted-service scaling",
    ]:
        assert phrase not in roadmap


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

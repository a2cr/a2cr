from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflows_cover_tests_build_and_security_audits():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    dependency_review = (ROOT / ".github" / "workflows" / "dependency-review.yml").read_text(encoding="utf-8")
    codeql = (ROOT / ".github" / "workflows" / "codeql.yml").read_text(encoding="utf-8")

    assert "python -m pytest -q" in ci
    assert "python -m pip_audit -r requirements.txt" in ci
    assert "npm audit --audit-level=high" in ci
    assert "npm run build" in ci
    assert "actions/dependency-review-action" in dependency_review
    assert "github/codeql-action/analyze" in codeql

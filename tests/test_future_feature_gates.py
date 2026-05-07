from pathlib import Path


def test_pr_template_requires_security_review_for_dangerous_future_features():
    template = (Path(__file__).resolve().parents[1] / ".github/pull_request_template.md").read_text(
        encoding="utf-8"
    )

    for term in (
        "file attachment",
        "file rendering",
        "URL fetch",
        "HTML/render preview",
        "shell/process execution",
        "AI-execution",
        "dedicated security review",
        "abuse-case regression tests",
        "rollback plan",
    ):
        assert term in template

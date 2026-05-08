from __future__ import annotations

import argparse
from sqlalchemy import text

from services.config import validate_runtime_environment
from services.data_lifecycle import global_orphan_data_lifecycle_scan
from services.db import get_web_engine


def expire_web_contexts() -> int:
    """Expire due Web SaaS contexts through the narrow DB function only."""
    validate_runtime_environment()
    with get_web_engine().begin() as conn:
        result = conn.execute(text("SELECT app.expire_contexts()"))
        return int(result.scalar_one())


def expire_work_stash() -> int:
    """Expire due WorkStash entries through the narrow DB function only."""
    validate_runtime_environment()
    with get_web_engine().begin() as conn:
        result = conn.execute(text("SELECT app.expire_work_stash()"))
        return int(result.scalar_one())


def prune_access_logs(*, older_than_seconds: int = 30 * 24 * 60 * 60, batch_size: int = 1000) -> int:
    """Prune old access logs through the narrow DB function only."""
    validate_runtime_environment()
    safe_older_than_seconds = max(int(older_than_seconds), 1)
    safe_batch_size = min(max(int(batch_size), 1), 10000)
    with get_web_engine().begin() as conn:
        result = conn.execute(
            text(
                """
                SELECT app.prune_access_logs(
                  (:older_than_seconds * interval '1 second'),
                  :batch_size
                )
                """
            ),
            {"older_than_seconds": safe_older_than_seconds, "batch_size": safe_batch_size},
        )
        return int(result.scalar_one())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A2CR maintenance commands")
    parser.add_argument("command", choices=["expire-contexts", "expire-work-stash", "prune-access-logs", "data-lifecycle-scan"])
    parser.add_argument("--older-than-seconds", type=int, default=30 * 24 * 60 * 60)
    parser.add_argument("--old-access-logs-older-than-seconds", type=int, default=30 * 24 * 60 * 60)
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args(argv)

    if args.command == "expire-contexts":
        count = expire_web_contexts()
        print(f"expired_contexts={count}")
        return 0
    if args.command == "expire-work-stash":
        count = expire_work_stash()
        print(f"expired_work_stash={count}")
        return 0
    if args.command == "prune-access-logs":
        count = prune_access_logs(
            older_than_seconds=args.older_than_seconds,
            batch_size=args.batch_size,
        )
        print(f"pruned_access_logs={count}")
        return 0
    if args.command == "data-lifecycle-scan":
        scan = global_orphan_data_lifecycle_scan(
            old_access_logs_older_than_seconds=args.old_access_logs_older_than_seconds,
        )
        for field in scan.counts:
            print(f"{field}={scan.counts[field]}")
        print(f"total_attention_rows={scan.total_attention_rows}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

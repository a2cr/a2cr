from __future__ import annotations

import argparse
from sqlalchemy import text

from services.config import validate_runtime_environment
from services.db import get_web_engine


def expire_web_contexts() -> int:
    """Expire due Web SaaS contexts through the narrow DB function only."""
    validate_runtime_environment()
    with get_web_engine().begin() as conn:
        result = conn.execute(text("SELECT app.expire_contexts()"))
        return int(result.scalar_one())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A2CR maintenance commands")
    parser.add_argument("command", choices=["expire-contexts"])
    args = parser.parse_args(argv)

    if args.command == "expire-contexts":
        count = expire_web_contexts()
        print(f"expired_contexts={count}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

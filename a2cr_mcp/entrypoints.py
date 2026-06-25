from __future__ import annotations

import os
import sys


def configure_local_env() -> None:
    os.environ["A2CR_MODE"] = "local"


def configure_cloud_env() -> None:
    os.environ["A2CR_MODE"] = "local"


def local_main() -> None:
    configure_local_env()
    from .server import main

    main()


def cloud_main() -> None:
    print(
        "a2cr-cloud-mcp has been discontinued. A2CR now runs as a local workspace MCP; "
        "use `a2cr-mcp` or `a2cr-local-mcp`.",
        file=sys.stderr,
    )
    raise SystemExit(2)

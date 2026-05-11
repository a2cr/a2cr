"""Compatibility entrypoint for the A2CR stdio MCP wrapper.

The installable PyPI package exposes the same server as `a2cr-mcp`.
Existing MCP configs that execute this file directly can keep working.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from a2cr_mcp.server import main


if __name__ == "__main__":
    main()

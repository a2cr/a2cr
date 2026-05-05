"""
MCP server entry point.
This wrapper removes the project root from sys.path before importing fastmcp,
preventing the local mcp/ directory from shadowing the installed mcp package.
"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))

# MCP stdio messages must stay UTF-8 on Windows too.
for stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

# Remove project root from sys.path so local mcp/ does not shadow installed mcp package
sys.path = [p for p in sys.path if p and os.path.abspath(p) != project_root]

# Execute the actual server
server_path = os.path.join(project_root, "mcp", "server.py")
with open(server_path, encoding="utf-8") as f:
    exec(compile(f.read(), server_path, "exec"))

"""Local-first A2CR workspace implementation."""

from .store import LocalWorkspaceStore, get_store

__all__ = ["LocalWorkspaceStore", "get_store"]

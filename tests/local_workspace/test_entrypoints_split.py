import os

from a2cr_mcp import entrypoints


def test_local_entrypoint_forces_local_mode():
    old_mode = os.environ.get("A2CR_MODE")
    os.environ.pop("A2CR_MODE", None)
    try:
        entrypoints.configure_local_env()

        assert os.environ["A2CR_MODE"] == "local"
    finally:
        _restore_mode(old_mode)


def test_cloud_entrypoint_no_longer_selects_cloud_mode():
    old_mode = os.environ.get("A2CR_MODE")
    os.environ["A2CR_MODE"] = "cloud"
    try:
        entrypoints.configure_cloud_env()

        assert os.environ["A2CR_MODE"] == "local"
    finally:
        _restore_mode(old_mode)


def _restore_mode(value: str | None) -> None:
    if value is None:
        os.environ.pop("A2CR_MODE", None)
    else:
        os.environ["A2CR_MODE"] = value

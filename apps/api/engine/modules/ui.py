"""Headless stub of modules.ui for the API.

The API never opens a Qt window — core.py only needs `update_status`, so we
provide a no-op implementation. Keeping the public surface tiny lets the
real PySide6-backed ui.py stay out of the import path.
"""

from __future__ import annotations

from typing import Optional, Callable


def update_status(message: str, scope: str = "DLC.CORE") -> None:
    """No-op status sink (was Qt-thread routed in the GUI build)."""
    return None


def check_and_ignore_nsfw(target, destroy: Optional[Callable] = None) -> bool:
    return False


def init(*_args, **_kwargs):
    raise RuntimeError("modules.ui.init() not supported in headless API build")

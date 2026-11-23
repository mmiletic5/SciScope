"""Opt-in, content-free failure diagnostics for the MVP server.

With ``SCISCOPE_DEBUG_FRAMES=1`` only traceback frame locations
(``path:line function``) and the exception class name are logged. Messages,
locals, and request or response content are never logged.
"""

from __future__ import annotations

import logging
import os
import traceback

ENV_NAME = "SCISCOPE_DEBUG_FRAMES"
_LOGGER = logging.getLogger("sciscope.debug_frames")


def log_failure_frames(exception: BaseException) -> None:
    """Log frames and the class name of ``exception`` when opted in.

    Args:
        exception: The failure being translated to an HTTP error response.
    """
    if os.environ.get(ENV_NAME) != "1":
        return
    frames = traceback.extract_tb(exception.__traceback__)
    lines = [f"{f.filename}:{f.lineno} {f.name}" for f in frames]
    _LOGGER.error(
        "debug_frames %s\n%s", type(exception).__name__, "\n".join(lines)
    )

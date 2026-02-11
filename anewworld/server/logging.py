"""
Logging configuration for the server.
"""

from __future__ import annotations

import logging
import os


def setup_logging(*, level: str | None = None) -> None:
    """
    Configure process-wide server logging.

    Parameters
    ----------
    level : str | None
        Logging level name (e.g. "DEBUG", "INFO", "WARNING").
        If None, reads ANEWORLD_LOG_LEVEL environment variable and
        defaults to "INFO".

    Returns
    -------
    None
    """
    lvl_name = (level or os.getenv("ANEWORLD_LOG_LEVEL") or "INFO").upper()
    lvl = getattr(logging, lvl_name, logging.INFO)

    logging.basicConfig(
        level=lvl,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.getLogger("asyncio").setLevel(logging.WARNING)

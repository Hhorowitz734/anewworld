"""
Server side configuration module.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServerConfig:
    """
    Configuration of anewworld server.
    """

    host: str = "0.0.0.0"
    """
    Host server IP.
    """

    port: int = 7777
    """
    Server port.
    """

    debug: bool = True
    """
    Debug flag.
    """

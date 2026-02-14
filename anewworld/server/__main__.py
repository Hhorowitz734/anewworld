"""
Entry point for running server.
"""

from __future__ import annotations

import asyncio
import logging
import socket

from anewworld.server import GameServer

from .config import ServerConfig
from .logging import setup_logging


async def main() -> None:
    """
    Game server run.
    """
    server_cfg = ServerConfig()
    setup_logging()
    logger = logging.getLogger(__name__)

    server = GameServer.new(
        debug=server_cfg.debug,
    )
    tcp = await asyncio.start_server(
        server.handle_client, host=server_cfg.host, port=server_cfg.port
    )

    sockets: tuple[socket.socket, ...] = tcp.sockets or ()
    binds = ", ".join(str(s.getsockname()) for s in sockets)
    if server_cfg.debug:
        logger.info("Server listening on %s", binds)

    async with tcp:
        await tcp.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

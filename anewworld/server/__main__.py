"""
Entry point for running server.
"""

from __future__ import annotations

import asyncio

from .config import ServerConfig
from .net import GameServer


async def main() -> None:
    """
    Game server run.
    """
    server_cfg = ServerConfig()

    server = GameServer.new()
    tcp = await asyncio.start_server(
        server.handle_client, host=server_cfg.host, port=server_cfg.port
    )
    async with tcp:
        await tcp.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

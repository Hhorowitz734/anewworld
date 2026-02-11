"""
Entry point for running server.
"""

from __future__ import annotations

import asyncio

from .net import GameServer


async def main() -> None:
    """
    Game server run.
    """
    server = GameServer.new()
    tcp = await asyncio.start_server(server.handle_client,
                                     host = "0.0.0.0",
                                     port = 7777)
    async with tcp:
        await tcp.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

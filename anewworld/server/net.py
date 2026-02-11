"""
Network server for basic player id assignment and session tracking.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

from .sessions import Session, SessionRegistry, new_player_id


def _dumps(obj: dict[str, Any]) -> bytes:
    """
    Encode a message as newline-delimited JSON bytes.

    Parameters
    ----------
    obj : dict[str, Any]
        Message object to encode.

    Returns
    -------
    bytes
        UTF-8 encoded JSON message terminated by a newline.
    """
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")


@dataclass(slots=True)
class GameServer:
    """
    Minimal TCP game server responsible for players.
    """

    sessions: SessionRegistry
    """
    Registry of currently connected player sessions.
    """

    @classmethod
    def new(cls) -> GameServer:
        """
        Construct a new game server instance.

        Returns
        -------
        GameServer
            Newly created server with an empty session registry.
        """
        return cls(sessions=SessionRegistry.new())

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Handle message processing for a single client.

        Parameters
        ----------
        reader : asyncio.StreamReader
            Stream reader associated with the client connection.
        writer : asyncio.StreamWriter
            Stream writer associated with the client connection.

        Returns
        -------
        None
        """
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                self.sessions.touch(writer)

                msg = self._parse(line)
                if msg is None:
                    await self._send(writer, {"t": "error", "reason": "bad_json"})
                    continue

                msg_type = msg.get("t")
                if msg_type == "request_id":
                    await self._handle_request_id(writer)
                    continue

                await self._send(
                    writer,
                    {"t": "error", "reason": "unknown_message"},
                )
        finally:
            self.sessions.remove_by_writer(writer)
            writer.close()
            await writer.wait_closed()

    def _parse(self, line: bytes) -> dict[str, Any] | None:
        """
        Parse a single newline-delimited JSON message.

        Parameters
        ----------
        line : bytes
            Raw bytes received from the client.

        Returns
        -------
        dict[str, Any] | None
            Parsed message dictionary if valid, otherwise None.
        """
        try:
            obj = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            return None

        if not isinstance(obj, dict):
            return None

        return obj

    async def _handle_request_id(
        self,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Handle a client request for a player identifier.

        If the client already has an assigned session, the existing
        player id is returned. Otherwise, a new player id is generated
        and the session is registered.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the requesting client.

        Returns
        -------
        None
        """
        existing_pid = self.sessions.by_writer.get(writer)
        if existing_pid is not None:
            await self._send(
                writer,
                {"t": "assign_id", "player_id": existing_pid},
            )
            return

        now = time.time()
        player_id = new_player_id()

        session = Session(
            player_id=player_id,
            writer=writer,
            connected_at_s=now,
            last_seen_s=now,
        )

        self.sessions.add(session)

        await self._send(
            writer,
            {"t": "assign_id", "player_id": player_id},
        )

    async def _send(
        self,
        writer: asyncio.StreamWriter,
        obj: dict[str, Any],
    ) -> None:
        """
        Send a single message to a client.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer for the client connection.
        obj : dict[str, Any]
            Message object to send.

        Returns
        -------
        None
        """
        writer.write(_dumps(obj))
        await writer.drain()

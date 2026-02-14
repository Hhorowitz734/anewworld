"""
Client networking utilities.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from anewworld.client.net.client_state import ClientState
from anewworld.shared.inventory import Inventory


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
class ServerConnection:
    """
    Connected client-side session to server.
    """

    host: str
    """
    Server host.
    """

    port: int
    """
    Server port.
    """

    reader: asyncio.StreamReader
    """
    Stream reader associated with the server connection.
    """

    writer: asyncio.StreamWriter
    """
    Stream writer associated with the server connection.
    """

    player_id: int
    """
    Assigned player id for this connection.
    """

    @classmethod
    async def connect(
        cls,
        *,
        host: str,
        port: int,
    ) -> tuple[ServerConnection, ClientState]:
        """
        Connect to the server, perform handshake, and bootstrap client state.

        Parameters
        ----------
        host : str
            Server host.
        port : int
            Server port.

        Returns
        -------
        tuple[ServerConnection, ClientState]
            Active connection and initialized client state.

        Raises
        ------
        RuntimeError
            If the server returns an unexpected response.
        """
        reader, writer = await asyncio.open_connection(host, port)

        writer.write(_dumps({"t": "request_id"}))
        await writer.drain()

        # --- Expect assign_id ---
        line = await reader.readline()
        if not line:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError("Server closed connection during handshake.")

        msg = cls._parse(line)
        if msg is None or msg.get("t") != "assign_id" or "player_id" not in msg:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError(f"Unexpected handshake response (assign_id): {line!r}")

        player_id = int(msg["player_id"])

        # --- Expect inventory snapshot ---
        line = await reader.readline()
        if not line:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError("Server closed connection during inventory bootstrap.")

        msg = cls._parse(line)
        if msg is None or msg.get("t") != "inventory" or "items" not in msg:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError(f"Unexpected handshake response (inventory): {line!r}")

        inventory = Inventory.from_wire(msg.get("items", {}))

        conn = cls(
            host=host,
            port=port,
            reader=reader,
            writer=writer,
            player_id=player_id,
        )

        state = ClientState(
            player_id=player_id,
            inventory=inventory,
        )

        return conn, state

    async def send(
        self,
        msg: dict[str, Any],
    ) -> None:
        """
        Send a single message to the server.

        Parameters
        ----------
        msg : dict[str, Any]
            Message to send.

        Returns
        -------
        None
        """
        self.writer.write(_dumps(msg))
        await self.writer.drain()

    async def recv(self) -> dict[str, Any]:
        """
        Receive a single message from the server.

        Returns
        -------
        dict[str, Any]
            Decoded message.

        Raises
        ------
        RuntimeError
            If the server closes the connection or sends invalid JSON.
        """
        line = await self.reader.readline()
        if not line:
            raise RuntimeError("Server closed connection.")

        msg = self._parse(line)
        if msg is None:
            raise RuntimeError(f"Bad JSON from server: {line!r}")

        return msg

    async def close(self) -> None:
        """
        Close the connection to the server.

        Returns
        -------
        None
        """
        self.writer.close()
        await self.writer.wait_closed()

    @staticmethod
    def _parse(line: bytes) -> dict[str, Any] | None:
        """
        Parse a single JSON line.

        Parameters
        ----------
        line : bytes
            Raw message bytes.

        Returns
        -------
        dict[str, Any] | None
            Parsed dict if valid, otherwise None.
        """
        try:
            obj = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            return None

        if not isinstance(obj, dict):
            return None

        return obj

"""
Client networking utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import asyncio
import json


def _dumps(obj: Dict[str, Any]) -> bytes:
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
    Stream writer associated with the server connecion.
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
        port: int
        ) -> ServerConnection:
        """
        Connect to the server and request PlayerId.

        Parameters
        ----------
        host : str
            Server host.
        port : int
            Server port.

        Returns
        -------
        ServerConnection
            Connected session with assigned player id.

        Raises
        ------
        RuntimeError
            If the server returns an unexpected response.
        """
        reader, writer = await asyncio.open_connection(host, port)

        writer.write(_dumps({"t": "request_id"}))
        await writer.drain()

        line = await reader.readline()
        if not line:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError("Server closed connection during handshake.")

        msg = cls._parse(line)
        if msg is None or msg.get("t") != "assign_id" or "player_id" not in msg:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError(f"Unexpected handshake response: {line!r}")

        player_id = int(msg["player_id"])
        return cls(host=host, port=port, reader=reader, writer=writer, player_id=player_id)

    async def send(self, msg: Dict[str, Any]) -> None:
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

    async def recv(self) -> Dict[str, Any]:
        """
        Receive a single message from the server.

        Returns
        -------
        dict[str, Any]
            Decoded message.

        Raises
        ------
        RuntimeError
            If the server closes the connection.
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
    def _parse(line: bytes) -> Optional[Dict[str, Any]]:
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

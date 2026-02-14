"""
Network server for basic player id assignment and session tracking.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from .inventory_registry import InventoryRegistry
from .sessions import Session, SessionRegistry, new_player_id

logger = logging.getLogger(__name__)


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

    inventories: InventoryRegistry
    """
    Registry of inventories of connected players.
    """

    debug: bool
    """
    Flag for whether to write debug messages.
    """

    @classmethod
    def new(cls, debug: bool = True) -> GameServer:
        """
        Construct a new game server instance.

        Parameters
        ----------
        debug : bool
            Flag for whether to write debug messages.

        Returns
        -------
        GameServer
            Newly created server with an empty session registry.
        """
        return cls(
            sessions=SessionRegistry.new(),
            inventories=InventoryRegistry.new(),
            debug=debug,
        )

    def _log_debug(self, msg: str, *args: Any) -> None:
        """
        Emit debug logs only when debug is enabled.

        Parameters
        ----------
        msg : str
            Logging format string.
        *args : Any
            Arguments interpolated into msg.

        Returns
        -------
        None
        """
        if self.debug:
            logger.debug(msg, *args)

    def _log_info(self, msg: str, *args: Any) -> None:
        """
        Emit info logs only when debug is enabled.

        Parameters
        ----------
        msg : str
            Logging format string.
        *args : Any
            Arguments interpolated into msg.

        Returns
        -------
        None
        """
        if self.debug:
            logger.info(msg, *args)

    def _log_warning(self, msg: str, *args: Any) -> None:
        """
        Emit warning logs only when debug is enabled.

        Parameters
        ----------
        msg : str
            Logging format string.
        *args : Any
            Arguments interpolated into msg.

        Returns
        -------
        None
        """
        if self.debug:
            logger.warning(msg, *args)

    def _log_exception(self, msg: str, *args: Any) -> None:
        """
        Emit exception logs only when debug is enabled.

        Parameters
        ----------
        msg : str
            Logging format string.
        *args : Any
            Arguments interpolated into msg.

        Returns
        -------
        None
        """
        if self.debug:
            logger.exception(msg, *args)

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
        peer = writer.get_extra_info("peername")
        self._log_info("Client connected: %s", peer)

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                self.sessions.touch(writer)

                msg = self._parse(line)
                if msg is None:
                    self._log_warning("Bad JSON from %s: %r", peer, line[:200])
                    await self._send(writer, {"t": "error", "reason": "bad_json"})
                    continue

                msg_type = msg.get("t")
                if msg_type == "request_id":
                    await self._handle_request_id(writer, peer=peer)
                    continue

                if msg_type == "request_inventory":
                    await self._handle_request_inventory(writer, peer=peer)
                    continue

                self._log_warning("Unknown message from %s: %s", peer, msg_type)
                await self._send(
                    writer,
                    {"t": "error", "reason": "unknown_message"},
                )
        except ConnectionResetError:
            self._log_info("Client reset connection: %s", peer)
        except Exception:
            self._log_exception("Unhandled error while serving client: %s", peer)
        finally:
            removed = self.sessions.remove_by_writer(writer)
            active = self.sessions.count()

            if removed is not None:
                self._log_info(
                    "Client disconnected: %s player_id=%d active=%d",
                    peer,
                    removed.player_id,
                    active,
                )
            else:
                self._log_info("Client disconnected: %s active=%d", peer, active)

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
        *,
        peer: Any,
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
        peer : Any
            Peer name reported by asyncio (typically (ip, port)).

        Returns
        -------
        None
        """
        existing_pid = self.sessions.by_writer.get(writer)
        if existing_pid is not None:
            self._log_debug(
                "Re-sent player_id=%d to %s (active=%d)",
                existing_pid,
                peer,
                self.sessions.count(),
            )
            await self._send(
                writer,
                {"t": "assign_id", "player_id": existing_pid},
            )
            inv = self.inventories.get_or_create(existing_pid)
            await self._send(
                writer,
                {"t": "inventory", "player_id": existing_pid, "items": inv.to_wire()},
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

        self._log_info(
            "Assigned player_id=%d to %s (active=%d)",
            player_id,
            peer,
            self.sessions.count(),
        )
        await self._send(
            writer,
            {"t": "assign_id", "player_id": player_id},
        )
        inv = self.inventories.get_or_create(player_id)
        await self._send(
            writer,
            {"t": "inventory", "player_id": player_id, "items": inv.to_wire()},
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

    async def _handle_request_inventory(
        self,
        writer: asyncio.StreamWriter,
        *,
        peer: Any,
    ) -> None:
        """
        Handle a client request for current inventory snapshot.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the requesting client.
        peer : Any
            Peer name reported by asyncio (typically (ip, port)).

        Returns
        -------
        None
        """
        player_id = self.sessions.by_writer.get(writer)
        if player_id is None:
            self._log_debug("Inventory requested before id assignment: %s", peer)
            await self._send(writer, {"t": "error", "reason": "no_player_id"})
            return

        inv = self.inventories.get_or_create(player_id)
        await self._send(
            writer,
            {"t": "inventory", "player_id": player_id, "items": inv.to_wire()},
        )

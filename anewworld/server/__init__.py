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
from .services.inventory_service import InventoryService
from .services.player_service import PlayerContext, PlayerService
from .services.world_service import WorldService
from .sessions import SessionRegistry
from .world_edits_registry import WorldEditsRegistry
from .world_edits_store import WorldEditsStore

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

    _player_service: PlayerService
    """
    Player service responsible for id assignment and session registration.
    """

    _inventory_service: InventoryService
    """
    Inventory service responsible for inventory requests and updates.
    """

    _world_service: WorldService
    """
    World service responsible for chunk subscriptions and world edit snapshots.
    """

    @classmethod
    def new(
        cls,
        *,
        debug: bool = True,
        chunk_size: int = 64,
        world_db_path: str = "server/data/world_edits.sqlite3",
        max_cached_chunks: int = 2048,
    ) -> GameServer:
        """
        Construct a new game server instance.

        Parameters
        ----------
        debug : bool
            Flag for whether to write debug messages.
        chunk_size : int
            Chunk width and height in tiles.
        world_db_path : str
            Path to sqlite database file for world edits.
        max_cached_chunks : int
            Maximum number of cached chunks to keep in memory.

        Returns
        -------
        GameServer
            Newly created server with service dependencies initialized.
        """
        sessions = SessionRegistry.new()
        inventories = InventoryRegistry.new()

        _player_service = PlayerService.new(sessions=sessions, debug=debug)

        _inventory_service = InventoryService.new(
            inventories=inventories,
            _player_service=_player_service,
            debug=debug,
        )

        store = WorldEditsStore.new(path=world_db_path)
        edits = WorldEditsRegistry.new(
            store=store,
            chunk_size=chunk_size,
            max_cached_chunks=max_cached_chunks,
        )

        _world_service = WorldService.new(
            edits=edits,
            sessions=sessions,
            _player_service=_player_service,
            debug=debug,
        )

        return cls(
            sessions=sessions,
            inventories=inventories,
            debug=debug,
            _player_service=_player_service,
            _inventory_service=_inventory_service,
            _world_service=_world_service,
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

                self._player_service.touch(writer)

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
                    await self._inventory_service.handle_request_inventory(
                        writer,
                        peer=peer,
                        send=self._send,
                    )
                    continue

                if msg_type == "sub_chunk":
                    await self._world_service.handle_sub_chunk(
                        writer,
                        msg,
                        peer=peer,
                        send=self._send,
                    )
                    continue

                if msg_type == "unsub_chunk":
                    await self._world_service.handle_unsub_chunk(
                        writer,
                        msg,
                        peer=peer,
                        send=self._send,
                    )
                    continue

                if msg_type == "request_chunk_edits":
                    await self._world_service.handle_request_chunk_edits(
                        writer,
                        msg,
                        peer=peer,
                        send=self._send,
                    )
                    continue

                self._log_warning("Unknown message from %s: %s", peer, msg_type)
                await self._send(writer, {"t": "error", "reason": "unknown_message"})
        except ConnectionResetError:
            self._log_info("Client reset connection: %s", peer)
        except Exception:
            self._log_exception("Unhandled error while serving client: %s", peer)
        finally:
            removed = self._player_service.remove_by_writer(writer)
            active = self.sessions.count()

            if removed is not None:
                self._world_service.on_disconnect(player_id=removed.player_id)
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
        ctx = PlayerContext(writer=writer, peer=peer, now_s=time.time())
        player_id = await self._player_service.handle_request_id(ctx, send=self._send)

        await self._inventory_service.send_inventory(
            writer,
            player_id=player_id,
            send=self._send,
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

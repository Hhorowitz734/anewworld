"""
World service responsible for chunk subscriptions and world edit snapshots.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from anewworld.server.sessions import SessionRegistry
from anewworld.server.world_edits_registry import WorldEditsRegistry

from .player_service import PlayerService

logger = logging.getLogger(__name__)

SendFn = Callable[[asyncio.StreamWriter, dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class WorldService:
    """
    World service responsible for chunk subscriptions and world edit snapshots.
    """

    edits: WorldEditsRegistry
    """
    World edits registry used to load persistent chunk overlays.
    """

    sessions: SessionRegistry
    """
    Session registry used to resolve player writers for broadcasting.
    """

    _player_service: PlayerService
    """
    Player service used to resolve the requesting player id.
    """

    debug: bool
    """
    Flag for whether to write debug messages.
    """

    _chunk_subs: dict[tuple[int, int], set[int]]
    """
    Mapping of (cx, cy) to subscribed player ids.
    """

    _player_subs: dict[int, set[tuple[int, int]]]
    """
    Mapping of player id to subscribed (cx, cy) chunks.
    """

    @classmethod
    def new(
        cls,
        *,
        edits: WorldEditsRegistry,
        sessions: SessionRegistry,
        _player_service: PlayerService,
        debug: bool,
    ) -> WorldService:
        """
        Construct a new world service.

        Parameters
        ----------
        edits : WorldEditsRegistry
            World edits registry used to load persistent chunk overlays.
        sessions : SessionRegistry
            Session registry used to resolve player writers for broadcasting.
        _player_service : PlayerService
            Player service used to resolve player id.
        debug : bool
            Flag for whether to write debug messages.

        Returns
        -------
        WorldService
            Newly created world service.
        """
        return cls(
            edits=edits,
            sessions=sessions,
            _player_service=_player_service,
            debug=debug,
            _chunk_subs={},
            _player_subs={},
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

    def on_disconnect(self, *, player_id: int) -> None:
        """
        Clean up subscriptions for a disconnected player.

        Parameters
        ----------
        player_id : int
            Player identifier.

        Returns
        -------
        None
        """
        chunks = self._player_subs.pop(player_id, None)
        if not chunks:
            return

        for key in chunks:
            subs = self._chunk_subs.get(key)
            if subs is None:
                continue
            subs.discard(player_id)
            if not subs:
                self._chunk_subs.pop(key, None)

    async def handle_sub_chunk(
        self,
        writer: asyncio.StreamWriter,
        msg: dict[str, Any],
        *,
        peer: Any,
        send: SendFn,
    ) -> None:
        """
        Subscribe the requesting player to a chunk and send snapshot.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the client connection.
        msg : dict[str, Any]
            Message payload containing 'cx' and 'cy'.
        peer : Any
            Peer name reported by asyncio (typically (ip, port)).
        send : SendFn
            Async callable of the form: await send(writer, obj).

        Returns
        -------
        None
        """
        player_id = self._player_service.get_player_id(writer)
        if player_id is None:
            self._log_debug("Chunk subscribed before id assignment: %s", peer)
            await send(writer, {"t": "error", "reason": "no_player_id"})
            return

        cx = msg.get("cx")
        cy = msg.get("cy")
        if not isinstance(cx, int) or not isinstance(cy, int):
            await send(writer, {"t": "error", "reason": "bad_chunk_coords"})
            return

        key = (cx, cy)
        self._chunk_subs.setdefault(key, set()).add(player_id)
        self._player_subs.setdefault(player_id, set()).add(key)

        snapshot = self.edits.get_chunk_snapshot(cx=cx, cy=cy)
        await send(writer, {"t": "chunk_edits", "cx": cx, "cy": cy, "edits": snapshot})

    async def handle_unsub_chunk(
        self,
        writer: asyncio.StreamWriter,
        msg: dict[str, Any],
        *,
        peer: Any,
        send: SendFn,
    ) -> None:
        """
        Unsubscribe the requesting player from a chunk.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the client connection.
        msg : dict[str, Any]
            Message payload containing 'cx' and 'cy'.
        peer : Any
            Peer name reported by asyncio (typically (ip, port)).
        send : SendFn
            Async callable of the form: await send(writer, obj).

        Returns
        -------
        None
        """
        player_id = self._player_service.get_player_id(writer)
        if player_id is None:
            self._log_debug("Chunk unsubscribed before id assignment: %s", peer)
            await send(writer, {"t": "error", "reason": "no_player_id"})
            return

        cx = msg.get("cx")
        cy = msg.get("cy")
        if not isinstance(cx, int) or not isinstance(cy, int):
            await send(writer, {"t": "error", "reason": "bad_chunk_coords"})
            return

        key = (cx, cy)

        chunks = self._player_subs.get(player_id)
        if chunks is not None:
            chunks.discard(key)
            if not chunks:
                self._player_subs.pop(player_id, None)

        subs = self._chunk_subs.get(key)
        if subs is not None:
            subs.discard(player_id)
            if not subs:
                self._chunk_subs.pop(key, None)

        await send(writer, {"t": "unsub_chunk_ok", "cx": cx, "cy": cy})

    async def handle_request_chunk_edits(
        self,
        writer: asyncio.StreamWriter,
        msg: dict[str, Any],
        *,
        peer: Any,
        send: SendFn,
    ) -> None:
        """
        Handle a client request for a chunk edits snapshot.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the client connection.
        msg : dict[str, Any]
            Message payload containing 'cx' and 'cy'.
        peer : Any
            Peer name reported by asyncio (typically (ip, port)).
        send : SendFn
            Async callable of the form: await send(writer, obj).

        Returns
        -------
        None
        """
        player_id = self._player_service.get_player_id(writer)
        if player_id is None:
            self._log_debug("Chunk edits requested before id assignment: %s", peer)
            await send(writer, {"t": "error", "reason": "no_player_id"})
            return

        cx = msg.get("cx")
        cy = msg.get("cy")
        if not isinstance(cx, int) or not isinstance(cy, int):
            await send(writer, {"t": "error", "reason": "bad_chunk_coords"})
            return

        snapshot = self.edits.get_chunk_snapshot(cx=cx, cy=cy)
        await send(writer, {"t": "chunk_edits", "cx": cx, "cy": cy, "edits": snapshot})

    async def broadcast_chunk(
        self,
        *,
        cx: int,
        cy: int,
        payload: dict[str, Any],
        send: SendFn,
    ) -> None:
        """
        Broadcast a message to all subscribers of a chunk.

        Parameters
        ----------
        cx : int
            Chunk x coordinate.
        cy : int
            Chunk y coordinate.
        payload : dict[str, Any]
            JSON-serializable message payload to send.
        send : SendFn
            Async callable of the form: await send(writer, obj).

        Returns
        -------
        None
        """
        subs = self._chunk_subs.get((cx, cy))
        if not subs:
            return

        for player_id in list(subs):
            sess = self.sessions.by_player.get(player_id)
            if sess is None:
                continue
            try:
                await send(sess.writer, payload)
            except ConnectionResetError:
                continue

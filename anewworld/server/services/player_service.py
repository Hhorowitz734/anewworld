"""
Player service responsible for player ids and sessions.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from anewworld.server.sessions import Session, SessionRegistry, new_player_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PlayerContext:
    """
    Context for player-related request.
    """

    writer: asyncio.StreamWriter
    """
    Stream writer associated with the client connection.
    """

    peer: Any
    """
    Peer name reported by asyncio.
    """

    now_s: float
    """
    Current server timestamp (seconds).
    """


@dataclass(slots=True)
class PlayerService:
    """
    Player service responsible for player id assignment and sessions.
    """

    sessions: SessionRegistry
    """
    Registry of currently connected player sessions.
    """

    debug: bool
    """
    Flag for whether to write debug messages.
    """

    @classmethod
    def new(cls, *, sessions: SessionRegistry, debug: bool) -> PlayerService:
        """
        Construct a new player service.

        Parameters
        ----------
        sessions : SessionRegistry
            Shared session registry.
        debug : bool
            Flag for whether to write debug messages.

        Returns
        -------
        PlayerService
            Newly create player service.
        """
        return cls(sessions=sessions, debug=debug)

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

    async def handle_request_id(
        self,
        ctx: PlayerContext,
        *,
        send: Any,
    ) -> int:
        """
        Handle a client request for a player identifier.

        Parameters
        ----------
        ctx : PlayerContext
            Context for this request.
        send: Any
            Async callable of the form: await send(writer, obj)

        Returns
        -------
        int
            Player id assigned to this connection.
        """
        existing_pid = self.sessions.by_writer.get(ctx.writer)
        if existing_pid is not None:
            self._log_debug(
                "Re-sent player_id=%d to %s (active=%d)",
                existing_pid,
                ctx.peer,
                self.sessions.count(),
            )
            await send(
                ctx.writer,
                {
                    "t": "assign_id",
                    "player_id": existing_pid,
                },
            )
            return existing_pid

        player_id = new_player_id()
        session = Session(
            player_id=player_id,
            writer=ctx.writer,
            connected_at_s=ctx.now_s,
            last_seen_s=ctx.now_s,
        )
        self.sessions.add(session)

        self._log_info(
            "Assigned player_id=%d to %s (active=%d)",
            player_id,
            ctx.peer,
            self.sessions.count(),
        )
        await send(ctx.writer, {"t": "assign_id", "player_id": player_id})
        return player_id

    def get_player_id(self, writer: asyncio.StreamWriter) -> int | None:
        """
        Get the player id for a connected client if assigned.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the client connection.

        Returns
        -------
        int | None
            Player id if assigned, otherwise None.
        """
        return self.sessions.by_writer.get(writer)

    def touch(self, writer: asyncio.StreamWriter) -> None:
        """
        Touch session for activity tracking.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the client connection.

        Returns
        -------
        None
        """
        self.sessions.touch(writer)

    def remove_by_writer(self, writer: asyncio.StreamWriter) -> Session | None:
        """
        Remove a session by writer (disconnect cleanup).

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the client connection.

        Returns
        -------
        Session | None
            Removed session if present, otherwise None.
        """
        return self.sessions.remove_by_writer(writer)

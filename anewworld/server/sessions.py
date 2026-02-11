"""
Sessions registry for connected clients.
"""

from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass

PlayerId = int


def new_player_id() -> PlayerId:
    """
    Generate a new player id.

    Returns
    -------
    PlayerId
        Random 64-bit id.
    """
    return secrets.randbits(64)


@dataclass(slots=True)
class Session:
    """
    Connected client session.
    """

    player_id: PlayerId
    """
    Unique player id for this player.
    """

    writer: asyncio.StreamWriter
    """
    Writer for this connection.
    """

    connected_at_s: float
    """
    Epoch timestamp when connected.
    """

    last_seen_s: float
    """
    Epoch timestamp of last received message.
    """


@dataclass(slots=True)
class SessionRegistry:
    """
    Registry of active connected sessions.
    """

    by_player: dict[PlayerId, Session]
    """
    Sessions keyed by player id.
    """

    by_writer: dict[asyncio.StreamWriter, PlayerId]
    """
    Reverse index to remove sessions on disconnect.
    """

    @classmethod
    def new(cls) -> SessionRegistry:
        """
        Construct an empty session registry.

        Returns
        -------
        SessionRegistry
            A new registry.
        """
        return cls(by_player={}, by_writer={})

    def add(self, sess: Session) -> None:
        """
        Add a session to the registry.

        Parameters
        ----------
        sess : Session
            Session to add.
        """
        self.by_player[sess.player_id] = sess
        self.by_writer[sess.writer] = sess.player_id

    def touch(self, writer: asyncio.StreamWriter) -> None:
        """
        Update last-seen timestamp for session.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Writer for the session to touch
        """
        pid = self.by_writer.get(writer)
        if pid is None:
            return
        sess = self.by_player.get(pid)
        if sess is None:
            return
        sess.last_seen_s = time.time()

    def remove_by_writer(self, writer: asyncio.StreamWriter) -> Session | None:
        """
        Remove a session using its writer.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Writer for the session.

        Returns
        -------
        Optional[Session]
            Removed session, if it existed.
        """
        pid = self.by_writer.pop(writer, None)
        if pid is None:
            return None
        return self.by_player.pop(pid, None)

    def count(self) -> int:
        """
        Count active sessions.

        Returns
        -------
        int
            Number of active sessions.
        """
        return len(self.by_player)

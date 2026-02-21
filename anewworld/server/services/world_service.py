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

from .player_service import PlayerService

logger = logging.getLogger(__name__)

SendFn = Callable[[asyncio.StreamWriter, dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class WorldService:
    """
    World service responsible for chunk subscriptions and world edit snapshots.
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
            sessions=sessions,
            _player_service=_player_service,
            debug=debug,
            _chunk_subs={},
            _player_subs={},
        )

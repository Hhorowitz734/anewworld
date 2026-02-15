"""
Client-side game state.
"""

from __future__ import annotations

from dataclasses import dataclass

from anewworld.shared.inventory import Inventory

from .world_edits_state import WorldEditsState


@dataclass(slots=True)
class ClientState:
    """
    Local client view of server authoritative state.
    """

    player_id: int
    """
    Player ID assigned by server.
    """

    inventory: Inventory
    """
    Latest inventory snapshot received from server.
    """

    world_edits: WorldEditsState
    """
    Latest world edits received frem server for subscribed chunks.
    """

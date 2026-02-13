"""
Client-side game state.
"""

from __future__ import annotations

from dataclasses import dataclass

from anewworld.shared.inventory import Inventory


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

    # TODO: Make sure this stores state and not client connection class

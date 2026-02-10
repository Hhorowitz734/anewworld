"""
Player top level management.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from anewworld.player.inventory import Inventory


@dataclass(slots=True)
class Player:
    """
    Client-side player state.

    This class holds only player-owned state.
    It does NOT modify the world directly.
    """

    player_id: int
    """
    Unique identifier for the player.
    In multiplayer, assigned by the server.
    """

    x_px: float
    """
    Player X position in world pixels.
    """

    y_px: float
    """
    Player Y position in world pixels.
    """

    inventory: Inventory
    """
    Player inventory (items the player owns).
    """

    selected_slot: int = 0
    """
    Currently selected inventory slot.
    """

    def tile_position(self, tile_size: int) -> tuple[int, int]:
        """
        Return the player's current tile coordinates.

        Parameters
        ----------
        tile_size : int
            Size of a tile in pixels.

        Returns
        -------
        (int, int)
            (tx, ty) tile coordinates.
        """
        return int(self.x_px // tile_size), int(self.y_px // tile_size)

    def select_slot(self, slot: int) -> None:
        """
        Select an inventory slot.
        """
        if 0 <= slot < self.inventory.size:
            self.selected_slot = slot

    def active_item(self) -> Optional[int]:
        """
        Return the item_id in the currently selected slot, if any.
        """
        stack = self.inventory.slots[self.selected_slot]
        if stack is None:
            return None
        return stack.item_id

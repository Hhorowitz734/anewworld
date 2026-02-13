"""
Server-side inventory storage keyed by player id.
"""

from __future__ import annotations

from dataclasses import dataclass

from anewworld.shared.inventory import Inventory


@dataclass(slots=True)
class InventoryRegistry:
    """
    In-memory inventory store for active players.
    """

    by_player_id: dict[int, Inventory]
    """
    Mapping from player id to inventory.
    """

    @classmethod
    def new(cls) -> InventoryRegistry:
        """
        Construct an empty registry.

        Returns
        -------
        InventoryRegistry
            Newly created registry.
        """
        return cls(by_player_id={})

    def get_or_create(self, player_id: int) -> Inventory:
        """
        Get inventory for a player (create if new).

        Parameters
        ----------
        player_id
            Player identifier.

        Returns
        -------
        Inventory
            Existing or newly created inventory.
        """
        inv = self.by_player_id.get(player_id)
        if inv is None:
            inv = Inventory.starter()
            self.by_player_id[player_id] = inv
        return inv

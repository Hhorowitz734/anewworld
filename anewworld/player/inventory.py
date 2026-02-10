"""
Player inventory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(slots=True)
class Inventory:
    """
    Extremely simple inventory.

    Maps item_id -> count.
    """

    items: Dict[str, int]

    @classmethod
    def with_houses(cls, count: int = 1) -> Inventory:
        """
        Convenience constructor for a starting inventory.
        """
        return cls(items={"houses": count})

    def has(self, item_id: str, count: int = 1) -> bool:
        """
        Check if the inventory has at least `count` of `item_id`.
        """
        return self.items.get(item_id, 0) >= count

    def remove(self, item_id: str, count: int = 1) -> bool:
        """
        Remove items if possible.

        Returns True if successful, False otherwise.
        """
        current = self.items.get(item_id, 0)
        if current < count:
            return False

        remaining = current - count
        if remaining > 0:
            self.items[item_id] = remaining
        else:
            del self.items[item_id]

        return True

    def add(self, item_id: str, count: int = 1) -> None:
        """
        Add items to the inventory.
        """
        self.items[item_id] = self.items.get(item_id, 0) + count

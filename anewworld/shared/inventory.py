"""
Player inventory model shared across client and server.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .resource import Resource


@dataclass(slots=True)
class Inventory:
    """
    Server authoritative inventory of resources.
    """

    amounts: dict[Resource, int] = field(default_factory=dict)
    """
    Mapping of resource type to non-negative quantity.
    """

    @classmethod
    def starter(cls) -> Inventory:
        """
        Construct a starter inventory for a newly created player.

        Returns
        -------
        Inventory
            Starter inventory with initial resources.
        """
        return cls(amounts={Resource.HOUSE: 1})

    def to_wire(self) -> dict[str, int]:
        """
        Convert inventory to JSON-serializable wire format.

        Returns
        -------
        dict[str, int]
            Mapping of resource key strings to quantities.
        """
        return {rt.value: qty for rt, qty in self.amounts.items()}

    @classmethod
    def from_wire(cls, obj: dict[str, int]) -> Inventory:
        """
        Parse inventory from wire format.

        Parameters
        ----------
        obj : dict[str, int]
            Mapping of resource key strings to quantities.

        Returns
        -------
        Inventory
            Parsed inventory instance.
        """
        amounts: dict[Resource, int] = {}
        for k, v in obj.items():
            try:
                rt = Resource(k)
            except ValueError:
                continue
            if isinstance(v, int) and v >= 0:
                amounts[rt] = v
        return cls(amounts=amounts)

    def get(self, resource: Resource) -> int:
        """
        Get quantity of a resource.

        Parameters
        ----------
        resource : Resource
            Resource type.

        Returns
        -------
        int
            Quantity owned (0 if absent).
        """
        return self.amounts.get(resource, 0)

    def has(self, resource: Resource, qty: int = 1) -> bool:
        """
        Check if inventory contains at least qty of resource.

        Parameters
        ----------
        resource : Resource
            Resource type.
        qty : int
            Required quantity.

        Returns
        -------
        bool
            True if sufficient quantity exists.
        """
        if qty <= 0:
            return True
        return self.get(resource) >= qty

    def add(self, resource: Resource, qty: int) -> None:
        """
        Add quantity of a resource.

        Parameters
        ----------
        resource : Resource
            Resource type.
        qty : int
            Quantity to add.

        Returns
        -------
        None
        """
        if qty <= 0:
            return
        self.amounts[resource] = self.get(resource) + qty

    def try_remove(self, resource: Resource, qty: int) -> bool:
        """
        Attempt to remove quantity of a resource.

        Parameters
        ----------
        resource : Resource
            Resource type.
        qty : int
            Quantity to remove.

        Returns
        -------
        bool
            True if removal succeeded, False otherwise.
        """
        if qty <= 0:
            return True

        current = self.get(resource)
        if current < qty:
            return False

        new_amount = current - qty
        if new_amount == 0:
            self.amounts.pop(resource, None)
        else:
            self.amounts[resource] = new_amount

        return True

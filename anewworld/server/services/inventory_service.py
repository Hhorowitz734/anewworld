"""
Inventory service responsible for inventory requests and updates.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from anewworld.server.inventory_registry import InventoryRegistry
from anewworld.shared.resource import Resource

from .player_service import PlayerService

logger = logging.getLogger(__name__)

SendFn = Callable[[asyncio.StreamWriter, dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class InventoryService:
    """
    Inventory service responsible for inventory requests and updates.
    """

    inventories: InventoryRegistry
    """
    Registry of inventories of connected players.
    """

    _player_service: PlayerService
    """
    Player service used to resolve the requesting player id.
    """

    debug: bool
    """
    Flag for whether to write debug messages.
    """

    @classmethod
    def new(
        cls,
        *,
        inventories: InventoryRegistry,
        _player_service: PlayerService,
        debug: bool,
    ) -> InventoryService:
        """
        Construct a new inventory service.

        Parameters
        ----------
        inventories : InventoryRegistry
            Shared inventory registry.
        _player_service : PlayerService
            Player service used to resolve player id.
        debug : bool
            Flag for whether to write debug messages.

        Returns
        -------
        InventoryService
            Newly created inventory service.
        """
        return cls(
            inventories=inventories,
            _player_service=_player_service,
            debug=debug,
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

    async def handle_request_inventory(
        self,
        writer: asyncio.StreamWriter,
        *,
        peer: Any,
        send: SendFn,
    ) -> None:
        """
        Handle a client request for current inventory snapshot.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the client connection.
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
            self._log_debug("Inventory requested before id assignment: %s", peer)
            await send(writer, {"t": "error", "reason": "no_player_id"})
            return

        inv = self.inventories.get_or_create(player_id)
        await send(
            writer,
            {"t": "inventory", "player_id": player_id, "items": inv.to_wire()},
        )

    async def send_inventory(
        self,
        writer: asyncio.StreamWriter,
        *,
        player_id: int,
        send: SendFn,
    ) -> None:
        """
        Send current inventory snapshot to a client.

        Parameters
        ----------
        writer : asyncio.StreamWriter
            Stream writer associated with the client connection.
        player_id : int
            Player identifier whose inventory should be sent.
        send : SendFn
            Async callable of the form: await send(writer, obj).

        Returns
        -------
        None
        """
        inv = self.inventories.get_or_create(player_id)
        await send(
            writer,
            {"t": "inventory", "player_id": player_id, "items": inv.to_wire()},
        )

    def try_consume(
        self,
        *,
        player_id: int,
        resource: Resource,
        qty: int,
    ) -> bool:
        """
        Attempt to consume a resource from a player's inventory.

        Parameters
        ----------
        player_id : int
            Player identifier whose inventory is modified.
        resource : Resource
            Resource type to consume.
        qty : int
            Quantity to consume.

        Returns
        -------
        bool
            True if removal succeeded, False otherwise.
        """
        if qty <= 0:
            return True

        inv = self.inventories.get_or_create(player_id)
        return inv.try_remove(resource, qty)

    def grant(
        self,
        *,
        player_id: int,
        resource: Resource,
        qty: int,
    ) -> None:
        """
        Grant a resource to a player's inventory.

        Parameters
        ----------
        player_id : int
            Player identifier whose inventory is modified.
        resource : Resource
            Resource type to grant.
        qty : int
            Quantity to grant.

        Returns
        -------
        None
        """
        if qty <= 0:
            return

        inv = self.inventories.get_or_create(player_id)
        inv.add(resource, qty)

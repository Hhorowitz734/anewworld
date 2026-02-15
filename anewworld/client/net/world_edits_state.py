"""
Client-side world edits state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from anewworld.shared.resource import Resource


@dataclass(frozen=True, slots=True)
class PlacedObject:
    """
    Placed object record received from the server.
    """

    obj: Resource
    """
    Object type identifier.
    """

    rot: int
    """
    Rotation / variant integer.
    """

    owner_id: int | None
    """
    Player id of the placer, if available.
    """

    updated_at_s: float
    """
    Server timestamp when last updated.
    """


@dataclass(slots=True)
class WorldEditsState:
    """
    Client-side state container for world edit overlays.
    """

    by_chunk: dict[tuple[int, int], dict[tuple[int, int], PlacedObject]] = field(
        default_factory=dict
    )
    """
    Mapping (cx, cy) -> mapping (lx, ly) -> placed object record.
    """

    def clear_chunk(self, *, cx: int, cy: int) -> None:
        """
        Remove all cached edits for a chunk.

        Parameters
        ----------
        cx : int
            Chunk x coordinate.
        cy : int
            Chunk y coordinate.

        Returns
        -------
        None
        """
        self.by_chunk.pop((cx, cy), None)

    def apply_chunk_snapshot(
        self, *, cx: int, cy: int, edits: list[dict[str, Any]]
    ) -> None:
        """
        Replace the entire edit overlay for a chunk using a server snapshot.

        Parameters
        ----------
        cx : int
            Chunk x coordinate.
        cy : int
            Chunk y coordinate.
        edits : list[dict[str, Any]]
            List of placement records in wire format.

        Returns
        -------
        None
        """
        chunk: dict[tuple[int, int], PlacedObject] = {}

        for rec in edits:
            lx = rec.get("lx")
            ly = rec.get("ly")
            obj = rec.get("obj")
            rot = rec.get("rot", 0)
            owner_id = rec.get("owner_id")
            updated_at_s = rec.get("updated_at_s", 0.0)

            if not isinstance(lx, int) or not isinstance(ly, int):
                continue
            if not isinstance(obj, str):
                continue
            if not isinstance(rot, int):
                continue
            if owner_id is not None and not isinstance(owner_id, int):
                continue
            if not isinstance(updated_at_s, int | float):
                continue

            try:
                res = Resource(obj)
            except ValueError:
                continue

            chunk[(lx, ly)] = PlacedObject(
                obj=res,
                rot=rot,
                owner_id=owner_id,
                updated_at_s=float(updated_at_s),
            )

        self.by_chunk[(cx, cy)] = chunk

    def apply_edit(self, msg: dict[str, Any]) -> tuple[int, int] | None:
        """
        Apply a single incremental edit message from the server.

        Parameters
        ----------
        msg : dict[str, Any]
            Message containing chunk coords and a place/remove operation.

        Returns
        -------
        tuple[int, int] | None
            (cx, cy) of the edited chunk if applied, otherwise None.
        """
        cx = msg.get("cx")
        cy = msg.get("cy")
        op = msg.get("op")
        lx = msg.get("lx")
        ly = msg.get("ly")

        if not isinstance(cx, int) or not isinstance(cy, int):
            return None
        if op not in ("place", "remove"):
            return None
        if not isinstance(lx, int) or not isinstance(ly, int):
            return None

        key = (cx, cy)
        chunk = self.by_chunk.get(key)
        if chunk is None:
            chunk = {}
            self.by_chunk[key] = chunk

        if op == "remove":
            chunk.pop((lx, ly), None)
            return key

        obj = msg.get("obj")
        rot = msg.get("rot", 0)
        owner_id = msg.get("owner_id")
        updated_at_s = msg.get("updated_at_s", 0.0)

        if not isinstance(obj, str):
            return None
        if not isinstance(rot, int):
            return None
        if owner_id is not None and not isinstance(owner_id, int):
            return None
        if not isinstance(updated_at_s, int | float):
            return None

        try:
            res = Resource(obj)
        except ValueError:
            return None

        chunk[(lx, ly)] = PlacedObject(
            obj=res,
            rot=rot,
            owner_id=owner_id,
            updated_at_s=float(updated_at_s),
        )

        return key

    def get_chunk(self, *, cx: int, cy: int) -> dict[tuple[int, int], PlacedObject]:
        """
        Retrieve the current overlay mapping for a chunk.

        Parameters
        ----------
        cx : int
            Chunk x coordinate.
        cy : int
            Chunk y coordinate.

        Returns
        -------
        dict[tuple[int, int], PlacedObject]
            Mapping from (lx, ly) to placed object record. If the chunk is not
            present, an empty mapping is returned.
        """
        return self.by_chunk.get((cx, cy), {})

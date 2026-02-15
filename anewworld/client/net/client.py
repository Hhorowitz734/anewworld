"""
Client networking utilities.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from anewworld.client.net.client_state import ClientState
from anewworld.client.net.world_edits_state import WorldEditsState
from anewworld.shared.inventory import Inventory


def _dumps(obj: dict[str, Any]) -> bytes:
    """
    Encode a message as newline-delimited JSON bytes.

    Parameters
    ----------
    obj : dict[str, Any]
        Message object to encode.

    Returns
    -------
    bytes
        UTF-8 encoded JSON message terminated by a newline.
    """
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")


@dataclass(slots=True)
class ServerConnection:
    """
    Connected client-side session to server.
    """

    host: str
    """
    Server host.
    """

    port: int
    """
    Server port.
    """

    reader: asyncio.StreamReader
    """
    Stream reader associated with the server connection.
    """

    writer: asyncio.StreamWriter
    """
    Stream writer associated with the server connection.
    """

    player_id: int
    """
    Assigned player id for this connection.
    """

    _subscribed_chunks: set[tuple[int, int]] = field(default_factory=set)
    """
    Currently subscribed chunks.
    """

    @classmethod
    async def connect(
        cls,
        *,
        host: str,
        port: int,
    ) -> tuple[ServerConnection, ClientState]:
        """
        Connect to the server, perform handshake, and bootstrap client state.

        Parameters
        ----------
        host : str
            Server host.
        port : int
            Server port.

        Returns
        -------
        tuple[ServerConnection, ClientState]
            Active connection and initialized client state.

        Raises
        ------
        RuntimeError
            If the server returns an unexpected response.
        """
        reader, writer = await asyncio.open_connection(host, port)

        writer.write(_dumps({"t": "request_id"}))
        await writer.drain()

        line = await reader.readline()
        if not line:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError("Server closed connection during handshake.")

        msg = cls._parse(line)
        if msg is None or msg.get("t") != "assign_id" or "player_id" not in msg:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError(f"Unexpected handshake response (assign_id): {line!r}")

        player_id = int(msg["player_id"])

        line = await reader.readline()
        if not line:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError("Server closed connection during inventory bootstrap.")

        msg = cls._parse(line)
        if msg is None or msg.get("t") != "inventory" or "items" not in msg:
            writer.close()
            await writer.wait_closed()
            raise RuntimeError(f"Unexpected handshake response (inventory): {line!r}")

        inventory = Inventory.from_wire(msg.get("items", {}))

        conn = cls(
            host=host,
            port=port,
            reader=reader,
            writer=writer,
            player_id=player_id,
            _subscribed_chunks=set(),
        )

        state = ClientState(
            player_id=player_id,
            inventory=inventory,
            world_edits=WorldEditsState(),
        )

        return conn, state

    async def send(
        self,
        msg: dict[str, Any],
    ) -> None:
        """
        Send a single message to the server.

        Parameters
        ----------
        msg : dict[str, Any]
            Message to send.

        Returns
        -------
        None
        """
        self.writer.write(_dumps(msg))
        await self.writer.drain()

    async def recv(self) -> dict[str, Any]:
        """
        Receive a single message from the server.

        Returns
        -------
        dict[str, Any]
            Decoded message.

        Raises
        ------
        RuntimeError
            If the server closes the connection or sends invalid JSON.
        """
        line = await self.reader.readline()
        if not line:
            raise RuntimeError("Server closed connection.")

        msg = self._parse(line)
        if msg is None:
            raise RuntimeError(f"Bad JSON from server: {line!r}")

        return msg

    async def close(self) -> None:
        """
        Close the connection to the server.

        Returns
        -------
        None
        """
        self.writer.close()
        await self.writer.wait_closed()

    async def tick(
        self,
        *,
        state: ClientState,
        camera_x_px: float,
        camera_y_px: float,
        screen_w_px: int,
        screen_h_px: int,
        chunk_size: int,
        tile_size: int,
        padding_chunks: int,
    ) -> set[tuple[int, int]]:
        """
        Update subscriptions for the current view and drain inbound messages.

        Parameters
        ----------
        state : ClientState
            Client state to update.
        camera_x_px : float
            Camera world x coordinate in pixels.
        camera_y_px : float
            Camera world y coordinate in pixels.
        screen_w_px : int
            Screen width in pixels.
        screen_h_px : int
            Screen height in pixels.
        chunk_size : int
            Chunk width/height in tiles.
        tile_size : int
            Tile size in pixels.
        padding_chunks : int
            Extra chunks to subscribe beyond viewport.

        Returns
        -------
        set[tuple[int, int]]
            Set of (cx, cy) chunks whose edits changed.
        """
        chunk_px = chunk_size * tile_size
        wanted = self._visible_chunks(
            camera_x_px=camera_x_px,
            camera_y_px=camera_y_px,
            screen_w_px=screen_w_px,
            screen_h_px=screen_h_px,
            chunk_px=chunk_px,
            padding_chunks=padding_chunks,
        )

        await self._sync_subscriptions(state=state, wanted=wanted)
        return await self.poll(state=state)

    async def _sync_subscriptions(
        self,
        *,
        state: ClientState,
        wanted: set[tuple[int, int]],
    ) -> None:
        """
        Subscribe and unsubscribe chunks to match a target set.

        Parameters
        ----------
        state : ClientState
            Client state to update when chunks are dropped.
        wanted : set[tuple[int, int]]
            Desired set of subscribed chunks.

        Returns
        -------
        None
        """
        to_sub = wanted - self._subscribed_chunks
        to_unsub = self._subscribed_chunks - wanted

        for cx, cy in to_sub:
            await self.send({"t": "sub_chunk", "cx": cx, "cy": cy})

        for cx, cy in to_unsub:
            await self.send({"t": "unsub_chunk", "cx": cx, "cy": cy})
            state.world_edits.clear_chunk(cx=cx, cy=cy)

        self._subscribed_chunks = wanted

    @staticmethod
    def _visible_chunks(
        *,
        camera_x_px: float,
        camera_y_px: float,
        screen_w_px: int,
        screen_h_px: int,
        chunk_px: int,
        padding_chunks: int,
    ) -> set[tuple[int, int]]:
        """
        Compute the chunk coordinates covering the current view.

        Parameters
        ----------
        camera_x_px : float
            Camera world x coordinate in pixels.
        camera_y_px : float
            Camera world y coordinate in pixels.
        screen_w_px : int
            Screen width in pixels.
        screen_h_px : int
            Screen height in pixels.
        chunk_px : int
            Chunk size in pixels.
        padding_chunks : int
            Extra chunks to include beyond viewport.

        Returns
        -------
        set[tuple[int, int]]
            Set of chunk (cx, cy) keys in view.
        """
        cam_x = int(round(camera_x_px))
        cam_y = int(round(camera_y_px))

        left = cam_x
        top = cam_y
        right = cam_x + screen_w_px
        bottom = cam_y + screen_h_px

        cx0 = (left // chunk_px) - padding_chunks
        cy0 = (top // chunk_px) - padding_chunks
        cx1 = ((right - 1) // chunk_px) + padding_chunks
        cy1 = ((bottom - 1) // chunk_px) + padding_chunks

        out: set[tuple[int, int]] = set()
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                out.add((cx, cy))
        return out

    @staticmethod
    def _parse(line: bytes) -> dict[str, Any] | None:
        """
        Parse a single JSON line.

        Parameters
        ----------
        line : bytes
            Raw message bytes.

        Returns
        -------
        dict[str, Any] | None
            Parsed dict if valid, otherwise None.
        """
        try:
            obj = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            return None

        if not isinstance(obj, dict):
            return None

        return obj

    async def poll(self, *, state: ClientState) -> set[tuple[int, int]]:
        """
        Drain any available server messages and update client state.

        Parameters
        ----------
        state : ClientState
            Client state to update.

        Returns
        -------
        set[tuple[int, int]]
            Set of (cx, cy) chunks whose edits changed.
        """
        changed_chunks: set[tuple[int, int]] = set()

        while True:
            try:
                msg = await asyncio.wait_for(self.recv(), timeout=0.0)
            except TimeoutError:
                break

            t = msg.get("t")

            if t == "inventory":
                items = msg.get("items")
                if isinstance(items, dict):
                    state.inventory = Inventory.from_wire(items)
                continue

            if t == "chunk_edits":
                cx = msg.get("cx")
                cy = msg.get("cy")
                edits = msg.get("edits")
                if (
                    isinstance(cx, int)
                    and isinstance(cy, int)
                    and isinstance(edits, list)
                ):
                    state.world_edits.apply_chunk_snapshot(cx=cx, cy=cy, edits=edits)
                    changed_chunks.add((cx, cy))
                continue

            if t == "edit_applied":
                key = state.world_edits.apply_edit(msg)
                if key is not None:
                    changed_chunks.add(key)
                continue

        return changed_chunks

"""
Module for player resources.
"""

from __future__ import annotations

from enum import StrEnum


class ResourceType(StrEnum):
    """
    Canonical resource identifiers.
    """

    # Placeable resources
    HOUSE = "house"

    # TODO: Make resources more complex
    # Use something like ResourceType (placeable/spendable)

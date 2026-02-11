"""
Generic definition for terrain classication levels.
"""

from enum import Enum
from typing import TypeVar


LevelT = TypeVar("LevelT", bound = Enum)
"""
Generic terrain level type.
"""

"""
Generic definition for terrain classication levels.
"""

from enum import Enum
from typing import TypeVar


Level = TypeVar("Level", bound = Enum)
"""
Generic terrain level type.
"""

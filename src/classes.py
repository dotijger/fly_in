from typing import Self
from enum import Enum


class AnsiColor(Enum):
    """ANSI escape codes used to color terminal output.

    Each member's value is the raw ANSI escape sequence that switches
    the terminal's foreground color (or, for ``RESET``, restores the
    default). Concatenate a member's ``value`` before text to color it,
    and append ``Color.RESET.value`` afterwards to stop the effect from
    bleeding into subsequent output.
    """

    RESET = "\033[0m"

    # Standard ANSI (16-color)
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"

    # Approximated via 256-color codes
    PURPLE = "\033[38;5;93m"
    ORANGE = "\033[38;5;208m"
    PINK = "\033[38;5;213m"
    BROWN = "\033[38;5;94m"
    GOLD = "\033[38;5;220m"


class ZoneType(Enum):
    NORMAL = 0
    PRIORITY = 1
    RESTRICTED = 2
    BLOCKED = 3


class Zone(BaseModel):
    coordinates: tuple[int, int] = ()
    color: str = ""
    name: str = ""
    max_drones: int = 1

    @model_validator(mode="after")
    def check(self) -> Self:
        x, y = self.coordinates
        if x < 0 or y < 0:
            raise ValueError(f"Coordinates of zone {self.name} cannot be negative.")
        if self.max_drones < 0:
            raise ValueError(f"Max drones of zone {self.name} cannot be negative.")
        return Self


class Connection(BaseModel):
    max_link_capacity: int = -1

    pass


class Simulation(BaseModel):
    pass

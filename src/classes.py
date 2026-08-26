from typing import Self
from pydantic import BaseModel, model_validator
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
    name: str
    x: int
    y: int
    metadata: str | None = None
    color: str | None = None
    max_drones: int = 1
    zone_type: str = "normal"

    @model_validator(mode="after")
    def check(self) -> Self:
        if self.metadata is not None:
            self._extract_metadata()
        if "-" in self.name:
            raise ValueError(
                f"{self.name} is invalid, zone names cannot contain dashes."
            )
        return self

    def _extract_metadata(self) -> None:
        if self.metadata is None:
            return
        self.metadata = self.metadata.lstrip("[")
        self.metadata = self.metadata.rstrip("]")
        data = self.metadata.split()
        for attribute in data:
            if attribute.startswith("color="):
                self.color = attribute.removeprefix("color=").strip()
            if attribute.startswith("max_drones="):
                try:
                    self.max_drones = int(attribute.removeprefix("max_drones=").strip())
                except ValueError:
                    raise ValueError(f"Max drones in {self.name} is not an integer.")
                if self.max_drones < 0:
                    raise ValueError(
                        f"Max drones of zone {self.name} cannot be negative."
                    )
            if attribute.startswith("zone="):
                self.zone_type = attribute.removeprefix("zone=").strip()
                types = ["normal", "priority", "restricted", "blocked"]
                if self.zone_type not in types:
                    raise ValueError(
                        f"Zone type of zone {self.name} is not a valid zone type."
                    )


class Connection(BaseModel):
    a: Zone
    b: Zone
    max_link_capacity: int = 1

    def other(self, place: Zone) -> Zone:
        return self.b if place == self.a else self.a


class Simulation(BaseModel):
    pass

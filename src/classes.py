from typing import Self, TypedDict
from pydantic import BaseModel, model_validator
from enum import Enum, auto


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
    NORMAL = auto()
    PRIORITY = auto()
    RESTRICTED = auto()
    BLOCKED = auto()


class HubType(Enum):
    START = "start_hub"
    NORMAL = "hub"
    END = "end_hub"


class Zone(BaseModel):
    kind: int
    name: str
    x: int
    y: int
    metadata: list[str] | None = None
    color: str | None = None
    max_drones: int = 1
    zone_type: str = "normal"
    cost: int = 1

    @model_validator(mode="after")
    def check(self) -> Self:
        if self.metadata is not None:
            self._extract_metadata()
        if "-" in self.name:
            raise ValueError(
                f"{self.name} is invalid, zone names cannot contain dashes."
            )
        if self.kind == 1 or self.kind == -1:
            self.max_drones = 1000
        return self

    def _extract_metadata(self) -> None:
        if self.metadata is None:
            return
        meta_string = " ".join(self.metadata)
        meta_string = meta_string.lstrip("[")
        meta_string = meta_string.rstrip("]")
        data = meta_string.split()
        for attribute in data:
            if attribute.startswith("color="):
                self.color = attribute.removeprefix("color=").strip()
            elif attribute.startswith("max_drones="):
                try:
                    self.max_drones = int(
                        attribute.removeprefix("max_drones=").strip()
                    )
                except ValueError:
                    raise ValueError(
                        f"Max drones in {self.name} is not an integer."
                    )
                if self.max_drones < 0:
                    raise ValueError(
                        f"Max drones of zone {self.name} cannot be negative."
                    )
            elif attribute.startswith("zone="):
                self.zone_type = attribute.removeprefix("zone=").strip()
                types = ["normal", "priority", "restricted", "blocked"]
                if self.zone_type not in types:
                    raise ValueError(
                        f"Zone type of zone {self.name} is not a valid zone type."
                    )
                if self.zone_type == "restricted":
                    self.cost = 2


class Connection(BaseModel):
    a: Zone
    b: Zone
    max_link_capacity: int = 1
    using: int = 0

    def other(self, place: Zone) -> Zone | None:
        if place != self.a and place != self.b:
            return None
        return self.b if place == self.a else self.a

    @property
    def name(self) -> str:
        return f"{self.a.name}-{self.b.name}"


class DroneStatus(str, Enum):
    AT_ZONE = "at_zone"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"


class Drone(BaseModel):
    id: str
    current: Zone
    remaining_path: list[Zone]
    status: DroneStatus = DroneStatus.AT_ZONE
    transit_connection: Connection | None = None
    transit_turns_left: int = 0

    def next_hub(self) -> Zone | None:
        return self.remaining_path[0] if self.remaining_path else None

    def start_transit(self, connection: Connection, cost: int) -> None:
        self.transit_turns_left = cost - 1
        self.transit_connection = connection
        self.status = DroneStatus.IN_TRANSIT

    def stop_transit(self) -> None:
        self.transit_turns_left = 0
        self.transit_connection = None
        self.status = DroneStatus.AT_ZONE


class Movement(BaseModel):
    drone_id: str
    destination: str


class Record(BaseModel):
    number: int
    movements: list[Movement] = []

    def get_records(self) -> str:
        return " ".join(
            f"{m.drone_id}-{m.destination}" for m in self.movements
        )


class Network(BaseModel):
    name: str
    nb_drones: int
    zones: list[Zone]
    connections: list[Connection]


class MapDict(TypedDict):
    map_name: str
    nb_drones: int
    zones: list[Zone]
    connections: list[Connection]

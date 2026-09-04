from typing import Self
from pydantic import BaseModel, model_validator, Field
from enum import Enum


class HubType(Enum):
    START = "start_hub"
    NORMAL = "hub"
    END = "end_hub"


class Zone(BaseModel):
    kind: int
    name: str = Field(r"[]")
    x: int
    y: int
    metadata: list[str] | None = None
    color: str | None = None
    max_drones: int = Field(default=1, ge=1)
    zone_type: str = "normal"
    cost: int = 1

    @model_validator(mode="after")
    def check(self) -> Self:
        if self.metadata is not None:
            self._extract_metadata()
        if "-" in self.name or " " in self.name:
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
                if attribute.removeprefix("max_drones=") == "0":
                    raise ValueError(
                        f"zone '{self.name}' cannot have a max capacity \
of 0 drones."
                    )
                try:
                    self.max_drones = int(
                        attribute.removeprefix("max_drones=").strip()
                    )
                except ValueError:
                    raise ValueError(
                        f"max drones in {self.name} is not an integer."
                    )
                if self.max_drones < 0:
                    raise ValueError(
                        f"max drones of zone {self.name} cannot be negative."
                    )
            elif attribute.startswith("zone="):
                self.zone_type = attribute.removeprefix("zone=").strip()
                types = ["normal", "priority", "restricted", "blocked"]
                if self.zone_type not in types:
                    raise ValueError(
                        f"zone type of zone {self.name} is not a \
valid zone type.\nAllowed: 'normal', 'priority', 'blocked', 'restricted'."
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

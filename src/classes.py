from typing import Self
from pydantic import BaseModel, model_validator, Field
from enum import Enum


class HubType(Enum):
    """Line prefixes that declare a zone in a map file"""
    START = "start_hub"
    NORMAL = "hub"
    END = "end_hub"


class Zone(BaseModel):
    """A node of the network that drones can occupy.
 
    Attributes:
        - kind: 1 for the start hub, -1 for the end hub, 0 otherwise.
        - name: Unique zone name (no dashes or spaces).
        - x: Integer x coordinate.
        - y: Integer y coordinate.
        - metadata: Raw '[key=value ...]' tokens from the map line, if any.
        - color: Display color, or None.
        - max_drones: Zone capacity; forced to 1000 on start and end hubs.
        - zone_type: One of normal, priority, restricted or blocked.
        - cost: Turns needed to enter the zone (2 if restricted, else 1).
    """
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
        """Apply metadata and validate the zone after construction.
 
        Returns:
            The validated zone.
 
        Raises:
            ValueError: If the name contains a dash or space, or the
                metadata is invalid.
        """
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
        """Parse self.metadata into color, max_drones, zone_type, cost.
 
        Unknown keys are ignored.
 
        Raises:
            ValueError: If max_drones is not a positive integer or the
                zone type is not recognised.
        """
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
    """A bidirectional connection between two zones.
 
    Attributes:
        - a: First endpoint.
        - b: Second endpoint.
        - max_link_capacity: Drones allowed on the link at the same time.
        using: Drones currently on the link.
    """
    a: Zone
    b: Zone
    max_link_capacity: int = 1
    using: int = 0

    def other(self, place: Zone) -> Zone | None:
        """Return the hub opposite of 'place'.
 
        Args:
            place: One of the connection's hubs.
 
        Returns:
            The other hub, or None if 'place' does not exist in this link.
        """
        if place != self.a and place != self.b:
            return None
        return self.b if place == self.a else self.a

    @property
    def name(self) -> str:
        """str: the connecton name in 'a-b' form."""
        return f"{self.a.name}-{self.b.name}"


class DroneStatus(str, Enum):
    """Potential states of a drone during simulation"""
    AT_ZONE = "at_zone"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"


class Drone(BaseModel):
    """A single drone and its progress along its route.
 
    Attributes:
        - id: Identifier such as 'D1'.
        - current: Zone the drone is in (or departed from while in transit).
        - remaining_path: Zones still to visit, next one first.
        - status: Current lifecycle state.
        - transit_connection: Link being traversed while in transit.
        - transit_turns_left: Turns remaining before landing.
    """
    id: str
    current: Zone
    remaining_path: list[Zone]
    status: DroneStatus = DroneStatus.AT_ZONE
    transit_connection: Connection | None = None
    transit_turns_left: int = 0

    def next_hub(self) -> Zone | None:
        """Return the next zone on the route, or None if it is empty."""
        return self.remaining_path[0] if self.remaining_path else None

    def start_transit(self, connection: Connection, cost: int) -> None:
        """Put the drone on a connection for a move costing >1 turn.
 
        Args:
            - connection: The link being entered.
            - cost: Total turns the move takes (including this one).
        """
        self.transit_turns_left = cost - 1
        self.transit_connection = connection
        self.status = DroneStatus.IN_TRANSIT

    def stop_transit(self) -> None:
        """Clear transit state and mark the drone as standing in a zone."""
        self.transit_turns_left = 0
        self.transit_connection = None
        self.status = DroneStatus.AT_ZONE


class Movement(BaseModel):
    """One drone move within a turn.
 
    Attributes:
        - drone_id: Identifier of the moving drone.
        - destination: Zone or connection name the drone moved to.
    """
    drone_id: str
    destination: str


class Record(BaseModel):
    """All movements that happened during one simulation turn.
 
    Attributes:
        - number: Turn number, starting at 1.
        - movements: Moves made this turn.
    """

    number: int
    movements: list[Movement] = []

    def get_records(self) -> str:
        """Format the turn as 'D<ID>-<dest>' tokens separated by spaces."""
        return " ".join(
            f"{m.drone_id}-{m.destination}" for m in self.movements
        )


class Network(BaseModel):
    """A fully parsed map.
 
    Attributes:
        - name: Map file name.
        - nb_drones: Number of drones to route.
        - zones: All zones in definition order.
        - connections: All connections in definition order.
    """
    name: str
    nb_drones: int
    zones: list[Zone]
    connections: list[Connection]

from src.classes import Network, Zone, Connection, Drone, Record, DroneStatus
from src.error import SimulationError
from pydantic import BaseModel
from src.algorithm import PathFinder
from src.resolver import TurnResolver


class Simulation(BaseModel):
    """Runs every drone of a network from start to end, logging each turn.

    Attributes:
        - map: The network to simulate.
        - zone_by_name: Lookup of zone name -> Zone.
        - connection_by_name: Lookup of (a, b) name pair -> Connection.
        - log: One Record per simulated turn.
        - drones: All drones in the simulation.
        - path: Route from PathFinder as (zone name, cost) pairs.
    """
    map: Network
    zone_by_name: dict[str, Zone] = {}
    connection_by_name: dict[tuple[str, str], Connection] = {}
    log: list[Record] = []
    drones: list[Drone] = []
    path: list[tuple[str, int]] = []

    def _setup(self) -> None:
        """Build lookups, compute the route and spawn drones at the start.

        Raises:
            SimulationError: If the map has no start hub or the path
                references an unknown zone.
            PathError: If no route to the end hub exists.
        """
        start_hub = None
        for zone in self.map.zones:
            if zone.kind == 1:
                start_hub = zone
            self.zone_by_name[zone.name] = zone
        for connection in self.map.connections:
            a, b = connection.name.strip("<>").split("-")
            self.connection_by_name[(a, b)] = connection
        pathfinder = PathFinder(map=self.map)
        self.path = pathfinder.run()
        unpacked = self.unpacked_path()
        if not start_hub:
            raise SimulationError(
                "No start hub identified, aborting simulation."
            )
        amount = self.map.nb_drones
        for i in range(amount):
            drone_id = "D" + str(i + 1)
            self.drones.append(
                Drone(
                    id=drone_id, current=start_hub, remaining_path=unpacked[1:]
                )
            )

    def unpacked_path(self) -> list[Zone]:
        """Convert 'self.path' into the matching list of Zone objects.

        Returns:
            Zones along the route, start hub first.

        Raises:
            SimulationError: If a path entry has no registered zone.
        """
        unpacked = []
        for hub, _ in self.path:
            zone = self.zone_by_name.get(hub)
            if zone is None:
                raise SimulationError(
                    f"No registered zone found for {hub}, aborting."
                )
            unpacked.append(zone)
        return unpacked

    def run(self) -> list[Record]:
        """Simulate turns until every drone has arrived.

        Returns:
            The per-turn movement log.
        """
        self._setup()
        resolver = TurnResolver(
            zone_by_name=self.zone_by_name,
            connection_by_name=self.connection_by_name,
        )
        arrived_drones: list[Drone] = []
        i = 1
        while len(arrived_drones) < len(self.drones):
            turn_record = resolver.resolve(self.drones, i)
            self.log.append(turn_record)
            arrived_drones = [
                d for d in self.drones if d.status == DroneStatus.ARRIVED
            ]
            i += 1
        return self.log

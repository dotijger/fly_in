from src.classes import Zone, Connection, Drone, Record, DroneStatus, Movement
from src.error import SimulationError
from pydantic import BaseModel


class TurnResolver(BaseModel):
    zone_by_name: dict[str, Zone]
    connection_by_name: dict[tuple[str, str], Connection]

    def resolve(self, drones: list[Drone], turn: int) -> Record:
        record = Record(number=turn)
        in_transit_drones = [
            d for d in drones if d.status == DroneStatus.IN_TRANSIT
        ]
        proposing_drones = [
            d for d in drones if d.status == DroneStatus.AT_ZONE
        ]

        available_hub: dict[str, int] = {}
        for zone in self.zone_by_name.values():
            drone_count = 0
            for d in drones:
                if (
                    d.current.name == zone.name
                    and d.status != DroneStatus.ARRIVED
                ):
                    drone_count += 1
            available_hub[zone.name] = zone.max_drones - drone_count

        available_link: dict[str, int] = {}
        for connection in self.connection_by_name.values():
            available_link[connection.name] = connection.max_link_capacity

        landing = [d for d in in_transit_drones if d.transit_turns_left == 1]
        for d in landing:
            next = d.next_hub()
            if next is not None:
                available_hub[next.name] -= 1
            if next is None:
                raise SimulationError(
                    "Drone already arrived asking for landing."
                )
            record.movements.append(
                Movement(drone_id=d.id, destination=next.name)
            )
            _ = d.remaining_path.pop(0)
            if d.transit_connection is None:
                raise SimulationError(
                    "Landing drone does not have an active connection stated,\
aborting."
                )
            available_link[d.transit_connection.name] -= 1
            d.stop_transit()
            d.current = next
            if next.kind == -1:
                d.status = DroneStatus.ARRIVED

        # not used because this happens in the proposed part,
        # in the if type == restriced (!), but if cost > 2, it will be used!
        in_transit = [d for d in in_transit_drones if d.transit_turns_left > 1]
        for d in in_transit:
            d.transit_turns_left -= 1
            if d.transit_connection is None:
                raise SimulationError(
                    "In transit drone does not have a connection stated, \
aborting."
                )
            available_link[d.transit_connection.name] -= 1
            if d.transit_connection is None:
                raise SimulationError(
                    "Transit connection of in_transit drone not defined, \
aborting."
                )
            record.movements.append(
                Movement(drone_id=d.id, destination=d.transit_connection.name)
            )

        for d in proposing_drones:
            next = d.next_hub()
            if next is None:
                raise SimulationError(
                    f"Active labeled drone {d.id} has no remaining path, \
aborting."
                )
            if available_hub[next.name] <= 0:
                continue
            try:
                next_connection = self.connection_by_name[
                    (d.current.name, next.name)
                ]
            except KeyError:
                try:
                    next_connection = self.connection_by_name[
                        (next.name, d.current.name)
                    ]
                except KeyError:
                    raise SimulationError(
                        f"Connection between {d.current.name} and {next.name} \
not found, aborting."
                    )
            if available_link[next_connection.name] == 0:
                continue
            if next.zone_type == "restricted":
                d.start_transit(
                    connection=next_connection,
                    cost=next.cost,
                )
                available_link[next_connection.name] -= 1
                available_hub[d.current.name] += 1
                record.movements.append(
                    Movement(drone_id=d.id, destination=next_connection.name)
                )
            else:
                available_link[next_connection.name] -= 1
                available_hub[d.current.name] += 1
                available_hub[next.name] -= 1
                record.movements.append(
                    Movement(drone_id=d.id, destination=next.name)
                )
                d.remaining_path.pop(0)
                if len(d.remaining_path) == 0:
                    d.status = DroneStatus.ARRIVED
                d.current = next

        return record

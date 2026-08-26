from pathlib import Path
from src.classes import Zone, Connection, Simulation
from src.error import ParseError
from pydantic import BaseModel
from typing import TypedDict
import sys
import argparse


class MapDict(TypedDict):
    nb_drones: int
    zones: list[Zone]
    connections: list[Connection]


class Parser(BaseModel):
    input: Path

    def _import_maps(self) -> list[MapDict]:
        maps = []
        maps_tbr = list(self.input.rglob("*.txt"))
        if len(maps_tbr) > 1:
            for path in maps_tbr:
                maps.append(self._read_map(path))
        return maps

    def _read_map(self, loc: Path) -> MapDict:
        with open(loc, "r") as file:
            raw_text = file.readlines()
        nb_drones = 0
        zones = []
        zone_names = []
        connections = []
        for line in raw_text:
            line = line.strip()
            line = line.rstrip("\n")
            if line.startswith("nb_drones: "):
                drones_data = line.split()
                try:
                    nb_drones = int(drones_data[1])
                except ValueError:
                    print("Number of drones is not an integer.")
                    sys.exit(1)
            if (
                line.startswith("hub:")
                or line.startswith("start_hub:")
                or line.startswith("end_hub:")
            ):
                hub_data = line.split()
                metadata = False
                if len(hub_data) > 4:
                    metadata = True
                try:
                    if metadata:
                        new_hub = Zone(
                            name=hub_data[1],
                            x=int(hub_data[2]),
                            y=int(hub_data[3]),
                            metadata=hub_data[4],
                        )
                    else:
                        new_hub = Zone(name=hub_data[1], x=hub_data[2], y=hub_data[3])
                    zones.append(new_hub)
                    zone_names.append(hub_data[1])
                except ValueError as e:
                    print(
                        f"Faulty hub information: {e.errors()[0]['msg']} Found in {str(loc)}, aborting."
                    )
                    sys.exit(1)
                set_names = set(zone_names)
                if len(zone_names) != len(set_names):
                    raise ValueError(f"Hub names in map {str(loc)} are not unique.")
            if line.startswith("connection:"):
                connection_raw = line.removeprefix("connection: ").strip()
                connection_data = connection_raw.split("-")
                max_link_capacity = 1
                hub_names = []
                for hub in connection_data:
                    hub = hub.split(" ")
                    if len(hub) > 1:
                        try:
                            max_link_capacity = int(hub[1][-2])
                        except ValueError:
                            print(
                                f"max link capacity is not an integer for {line} in {str(loc)}."
                            )
                            sys.exit(1)
                    hub_names.append(hub[0])
                for hub in hub_names:
                    if hub not in zone_names:
                        raise ParseError(
                            f"{hub} in {line} is not a defined zone. Found in {str(loc)}"
                        )
                if len(connection_data) > 2:
                    raise ValueError(f"{line} has too many hubs specified.")
                zone_ab = []
                for hub in hub_names:
                    i = 0
                    for name in zone_names:
                        if hub == name:
                            zone_ab.append(zones[i])
                            break
                        i += 1
                try:
                    connection = Connection(
                        a=zone_ab[0], b=zone_ab[1], max_link_capacity=max_link_capacity
                    )
                    connections.append(connection)
                except ValueError as e:
                    print(
                        f"Fault connection data: {e.errors()[0]['msg']} Found in {str(loc)}."
                    )
        return {
            "nb_drones": nb_drones,
            "zones": zones,
            "connections": connections,
        }

    def print(self, maps: list[MapDict]) -> None:
        for data in maps:
            print(f"nb_drones: {data['nb_drones']}")
            print("\nZones:")
            for zone in data["zones"]:
                print(
                    f"  {zone.name:<12} ({zone.x},{zone.y})  "
                    f"type={zone.zone_type:<10} color={zone.color}  "
                    f"max_drones={zone.max_drones}"
                )
            print("\nConnections:")
            for conn in data["connections"]:
                print(
                    f"  {conn.a.name} <-> {conn.b.name}  (capacity={conn.max_link_capacity})"
                )


if __name__ == "__main__":
    parse = Parser(input=Path("maps"))
    try:
        maps = parse._import_maps()
        parse.print(maps)
    except (ParseError, ValueError) as e:
        print(e)
        sys.exit(1)

from pathlib import Path
from src.classes import Zone, Connection, Network
from src.error import ParseError
from pydantic import BaseModel, ValidationError
import sys


class Parser(BaseModel):
    input: Path
    zones: list[Zone] = []
    connections: list[Connection] = []
    nb_drones: int | None = None
    seen_connections: set[frozenset[str]] = set()

    def _import_maps(self) -> list[Network]:
        maps = []
        maps_tbr = list(self.input.rglob("*.txt"))
        if len(maps_tbr) >= 1:
            for path in maps_tbr:
                try:
                    self.zones = []
                    self.connections = []
                    self.nb_drones = None
                    self.seen_connections = set()
                    self._check_definition_order(path)
                    self._check_empty_file(path)
                except ParseError as e:
                    print(e)
                    sys.exit(1)
                maps.append(self._read_map(path))
        return maps

    def _check_empty_file(self, loc: Path) -> None:
        with open(loc, "r") as file:
            raw_text = file.readlines()
        if len(raw_text) == 0:
            raise ParseError(str(loc), 0, "", "Map file is completely empty.")
        nb_drones, zones, connections = False, False, False
        for number, line in enumerate(raw_text, start=1):
            line = line.strip()
            line.rstrip("\n")
            if line.startswith("nb_drones: "):
                nb_drones = True
            elif (
                line.startswith("start_hub: ")
                or line.startswith("hub: ")
                or line.startswith("end_hub: ")
            ):
                zones = True
            elif line.startswith("connections: "):
                connections = True
        if not nb_drones and not zones and not connections:
            raise ParseError(
                str(loc),
                0,
                "",
                "Map file contains no definitions whatsoever.",
            )

    def _check_definition_order(self, loc: Path) -> None:
        with open(loc, "r") as file:
            raw_text = file.readlines()
        nb_drones = True
        zones = False
        nb_zones = 0
        connections = False
        for number, line in enumerate(raw_text, start=1):
            if line.startswith("#"):
                continue
            line = line.strip()
            line.rstrip("\n")
            if line == "" or line.isspace():
                continue
            if line.startswith("nb_drones: "):
                if nb_drones:
                    zones = True
                    nb_drones = False
                    continue
                else:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Number of drones is already defined.",
                    )
            elif (
                line.startswith("start_hub: ")
                or line.startswith("hub: ")
                or line.startswith("end_hub: ")
            ):
                if zones:
                    nb_zones += 1
                    continue
                elif connections:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Hubs cannot be defined after connections.",
                    )
                else:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Hubs cannot be defined before number of drones \
has been defined.",
                    )
            elif line.startswith("connection: "):
                if not connections:
                    if nb_drones:
                        raise ParseError(
                            str(loc),
                            number,
                            line,
                            "Connections cannot be defined before number \
of drones has been defined.",
                        )
                    elif nb_zones == 0:
                        raise ParseError(
                            str(loc),
                            number,
                            line,
                            "No connections can be defined if there are no \
hubs defined.",
                        )
                    else:
                        zones = False
                        connections = True
                        continue
                if connections:
                    if nb_zones == 0:
                        raise ParseError(
                            str(loc),
                            number,
                            line,
                            "No connections can be defined if there are no \
hubs defined.",
                        )

    def _read_map(self, loc: Path) -> Network:
        with open(loc, "r") as file:
            raw_text = file.readlines()

        zone_names = []
        start_hubs = 0
        end_hubs = 0
        for number, line in enumerate(raw_text, start=1):
            if line.startswith("#"):
                continue
            line = line.strip()
            line = line.rstrip("\n")
            if line.startswith("nb_drones: "):
                drones_data = line.split()
                try:
                    self.nb_drones = int(drones_data[1])
                except ValueError:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Number of drones is not an integer.",
                        "nb_drones: <positive_integer>",
                    )
                    sys.exit(1)
            if self.nb_drones is None:
                raise ParseError(
                    str(loc),
                    number,
                    line,
                    "nb_drones definition not found before other definitions.",
                    "nb_drones: <positive_integer>",
                )
                sys.exit(1)
            if self.nb_drones <= 0:
                raise ParseError(
                    str(loc),
                    number,
                    line,
                    "Number of drones is not a positive integer.",
                    "nb_drones: <positive_integer>",
                )
                sys.exit(1)
            if (
                line.startswith("hub:")
                or line.startswith("start_hub:")
                or line.startswith("end_hub:")
            ):
                start = 0
                if line.startswith("end_hub:"):
                    end_hubs += 1
                    start = -1
                elif line.startswith("start_hub:"):
                    start_hubs += 1
                    start = 1
                if start_hubs > 1 or end_hubs > 1:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "There may only be one start and end hub defined.",
                    )
                hub_data = line.split()
                metadata = False
                try:
                    float(hub_data[2])
                except ValueError:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Hub name cannot contain white space.",
                        "hub: <name> <x> <y>",
                    )
                if len(hub_data) > 4:
                    if not hub_data[4].startswith("[") or not hub_data[
                        -1
                    ].endswith("]"):
                        raise ParseError(
                            str(loc),
                            number,
                            line,
                            "Incorrect metadata format",
                            "hub: <name> <x> <y> [metadata_type=value]\n\
types of metadata: 'zone', 'max_drones', 'color'",
                        )
                        sys.exit(1)
                    metadata = True
                if len(hub_data) < 4:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Incomplete hub definition.",
                        "hub: <name> <x> <y>",
                    )
                    sys.exit(1)
                try:
                    if metadata:
                        if not self._check_valid_metadata(hub_data[4]):
                            raise ParseError(
                                str(loc),
                                number,
                                line,
                                "metadata [key=value] pairs are incomplete.",
                            )
                        new_hub = Zone(
                            kind=start,
                            name=hub_data[1],
                            x=int(hub_data[2]),
                            y=int(hub_data[3]),
                            metadata=hub_data[4:],
                        )
                    else:
                        new_hub = Zone(
                            kind=start,
                            name=hub_data[1],
                            x=int(hub_data[2]),
                            y=int(hub_data[3]),
                        )
                    self.zones.append(new_hub)
                    zone_names.append(hub_data[1])
                except ValidationError as e:
                    messages = "; ".join(err["msg"] for err in e.errors())
                    raise ParseError(str(loc), number, line, f"{messages}")
                except ValueError:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Hub coordinates have to be integers.",
                        "<hub>: <name> <int> <int>",
                    )
                    sys.exit(1)
                set_names = set(zone_names)
                if len(zone_names) != len(set_names):
                    raise ParseError(
                        str(loc), number, line, "Hub names have to be unique."
                    )
            if line.startswith("connection:"):
                connection_raw = line.removeprefix("connection: ").strip()
                connection_data = connection_raw.split("-")
                max_link_capacity = 1
                hub_names = []
                for hub in connection_data:
                    hubs = hub.split(" ")
                    if len(hubs) > 1:
                        try:
                            max_link_capacity = int(hubs[1][-2])
                        except ValueError:
                            raise ParseError(
                                str(loc),
                                number,
                                line,
                                "'max_link_capacity' is not defined as a \
positive integer.",
                            )
                            sys.exit(1)
                    hub_names.append(hubs[0])
                for hub in hub_names:
                    if hub not in zone_names:
                        raise ParseError(
                            str(loc),
                            number,
                            line,
                            f"Connection contains an undefined zone: '{hub}'. \
Connections can only be made between two predefined zones.",
                        )
                if len(connection_data) > 2:
                    raise ValueError(f"{line} has too many hubs specified.")
                zone_ab = []
                for hub in hub_names:
                    i = 0
                    for name in zone_names:
                        if hub == name:
                            zone_ab.append(self.zones[i])
                            break
                        i += 1
                if zone_ab[0] == zone_ab[1]:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Connections cannot exist between the same hub.",
                    )
                if self._check_duplicate_connections(zone_ab):
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Duplicate connections are not allowed.",
                    )
                try:
                    connection = Connection(
                        a=zone_ab[0],
                        b=zone_ab[1],
                        max_link_capacity=max_link_capacity,
                    )
                    self.seen_connections.add(
                        frozenset({connection.a.name, connection.b.name})
                    )
                    self.connections.append(connection)
                except ValidationError as e:
                    messages = "; ".join(err["msg"] for err in e.errors())
                    raise ParseError(str(loc), number, line, f"{messages}")
        path_to_str = str(loc)
        sliced = path_to_str.split("/")
        if self.nb_drones is None:
            raise ParseError(
                str(loc),
                0,
                "",
                "After parsing, no number of drones has been found in .txt,\
 aborting.",
            )
        return Network(
            name=sliced[-1],
            nb_drones=self.nb_drones,
            zones=self.zones,
            connections=self.connections,
        )

    @staticmethod
    def _check_valid_metadata(metadata: str) -> bool:
        valid = False
        for c in metadata:
            if c == "=":
                valid = not valid
        return valid

    def _check_duplicate_connections(self, zones: list[Zone]) -> bool:
        key = frozenset({zones[0].name, zones[1].name})
        return key in self.seen_connections

    def print(self, network: Network) -> None:
        print(f"nb_drones: '{network.nb_drones}'")
        print("\nZones:")
        for zone in network.zones:
            print(
                f"  {zone.name:<12} ({zone.x},{zone.y})  "
                f"type={zone.zone_type:<10} color={zone.color}  "
                f"max_drones={zone.max_drones}"
            )
        print("\nConnections:")
        for conn in network.connections:
            print(
                f"  {conn.a.name} <-> {conn.b.name}  \
(capacity={conn.max_link_capacity})"
            )


if __name__ == "__main__":
    parse = Parser(input=Path("maps"))
    try:
        maps = parse._import_maps()
        for map in maps:
            parse.print(map)
    except (ParseError, ValueError) as e:
        print(e)
        sys.exit(1)

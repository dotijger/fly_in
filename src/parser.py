from pathlib import Path
from src.classes import Zone, Connection, Network
from src.error import ParseError
from pydantic import BaseModel, ValidationError
import sys


class Parser(BaseModel):
    """Reads and validates map files into Network objects.

    Attributes:
        - input: Directory searched recursively for ``*.txt`` maps.
        - zones: Zones collected for the map currently being parsed.
        - connections: Connections collected for the current map.
        - nb_drones: Drone count of the current map, once read.
        - seen_connections: Unordered name pairs, used to reject duplicates.
    """
    input: Path
    zones: list[Zone] = []
    connections: list[Connection] = []
    nb_drones: int | None = None
    seen_connections: set[frozenset[str]] = set()

    def _import_maps(self) -> list[Network]:
        """Parse every *.txt map found under 'self.input'.

        Parser state is reset before each file. Pre-check failures print
        the error and exit the program.

        Returns:
            One Network per map file.

        Raises:
            ParseError: If a map fails validation while being read.
        """
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
        """Reject files that are empty or contain no definitions.

        Args:
            loc: Path of the map file.

        Raises:
            ParseError: If the file is empty or has no recognised lines.
        """
        with open(loc, "r") as file:
            raw_text = file.readlines()
        if len(raw_text) == 0:
            raise ParseError(str(loc), 0, "", "Map file is completely empty.")
        nb_drones, zones, connections = False, False, False
        for number, line in enumerate(raw_text, start=1):
            line = line.strip()
            if line.startswith("nb_drones: "):
                nb_drones = True
            elif (
                line.startswith("start_hub: ")
                or line.startswith("hub: ")
                or line.startswith("end_hub: ")
            ):
                zones = True
            elif line.startswith("connection: "):
                connections = True
        if not nb_drones and not zones and not connections:
            raise ParseError(
                str(loc),
                0,
                "",
                "Map file contains no definitions whatsoever.",
            )

    def _check_definition_order(self, loc: Path) -> None:
        """Check that sections appear as nb_drones >> hubs >> connections.

        Comments and blank lines are skipped.

        Args:
            loc: Path of the map file.

        Raises:
            ParseError: On a repeated nb_drones line or out-of-order section.
        """
        with open(loc, "r") as file:
            raw_text = file.readlines()
        nb_drones = True
        zones = False
        nb_zones = 0
        connections = False
        for number, raw in enumerate(raw_text, start=1):
            line = raw.split('#', 1)[0].strip()
            if not line:
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
        """Parse one map file into a Network.

        Handles the drone count, hub lines (with optional metadata) and
        connection lines (with optional max_link_capacity), validating
        uniqueness, references and duplicates as it goes.

        Args:
            loc: Path of the map file.

        Returns:
            The parsed network, named after the file.

        Raises:
            ParseError: On any syntax or validation error, with line info.
            ValueError: If a connection names more than two hubs.
        """
        with open(loc, "r") as file:
            raw_text = file.readlines()

        zone_names = []
        start_hubs = 0
        end_hubs = 0
        for number, raw in enumerate(raw_text, start=1):
            line = raw.split('#', 1)[0].strip()
            if not line:
                continue
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
                if self.nb_drones <= 0:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Number of drones is not a positive integer.",
                        "nb_drones: <positive_integer>",
                    )
            elif (
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
                if len(hub_data) < 4:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Incomplete hub definition.",
                        "hub: <name> <x> <y>",
                    )
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
                    metadata = True
                try:
                    if metadata:
                        error = self._check_valid_metadata(hub_data[4:])
                        if error:
                            raise ParseError(
                                    str(loc),
                                    number,
                                    line,
                                    error,
                                    "[zone=<type> color=<value>\
     max_drones=<int>]",
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
                set_names = set(zone_names)
                if len(zone_names) != len(set_names):
                    raise ParseError(
                        str(loc), number, line, "Hub names have to be unique."
                    )
            elif line.startswith("connection:"):
                connection_raw = line.removeprefix("connection: ").strip()
                connection_data = connection_raw.split("-")
                max_link_capacity = 1
                hub_names = []
                for hub in connection_data:
                    hubs = hub.split(" ")
                    if len(hubs) > 1:
                        meta = hubs[1].strip('[]')
                        key, sep, value = meta.partition('=')
                        if (
                            key != "max_link_capacity"
                            or not sep
                            or not value.isdigit()
                        ):
                            raise ParseError(
                                str(loc),
                                number,
                                line,
                                "Incorrect spec of connection metadata.")
                        max_link_capacity = int(value)
                        if max_link_capacity < 1:
                            raise ParseError(
                                str(loc),
                                number,
                                line,
                                "'max_link_capacity' is not defined as a \
positive integer.",
                            )
                    hub_names.append(hubs[0])
                if len(hub_names) != 2 or "" in hub_names:
                    raise ParseError(
                        str(loc),
                        number,
                        line,
                        "Connections need exactly two hubs.",
                        "connection: <zone1>-<zone2> [metadata]"
                    )
                for hub in hub_names:
                    if hub not in zone_names:
                        raise ParseError(
                            str(loc),
                            number,
                            line,
                            f"Connection contains an undefined zone: '{hub}'. \
Connections can only be made between two predefined zones.",
                        )
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
            else:
                raise ParseError(
                    str(loc),
                    number,
                    line,
                    "Unknown line type.")
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
        if end_hubs != 1 or start_hubs != 1:
            raise ParseError(
                str(loc),
                0,
                "",
                "After parsing, no start or end hubs were found in .txt,\
    aborting.",
            )
        return Network(
            name=sliced[-1],
            nb_drones=self.nb_drones,
            zones=self.zones,
            connections=self.connections,
        )

    @staticmethod
    def _check_valid_metadata(metadata: list[str]) -> str | None:
        """Check a hub's metadata block for validity.

        Args:
            metadata: Everything after the coordinates in a list of strings

        Returns:
            A string containing an error if found, otherwise None on success.
        """
        full = " ".join(metadata)
        if not full.startswith('[') or not full.endswith(']'):
            return "Metadata must be enclosed in []"
        full = full[1:-1].strip()
        if '[' in full or ']' in full:
            return "Metadata may only be one [] block"
        if not full:
            return "Metadata block is empty"
        valid_meta_keys = ("zone", "color", "max_drones")
        seen: set[str] = set()
        for item in full.split():
            if item.count("=") != 1:
                return f"{item} is not a key=value pair"
            k, v = item.split('=')
            if not k or not v:
                return f"{item} is missing key or value"
            if k not in valid_meta_keys:
                return f"Unknown metadata key: {k}"
            if k in seen:
                return f"Metadata key '{k}' has already been defined."
            seen.add(k)
        return None

    def _check_duplicate_connections(self, zones: list[Zone]) -> bool:
        """Tell whether a connection between two zones was already seen.

        Args:
            zones: The two endpoints; order does not matter.

        Returns:
            True if the pair is already in 'seen_connections'.
        """
        key = frozenset({zones[0].name, zones[1].name})
        return key in self.seen_connections

    def print(self, network: Network) -> None:
        """Print a readable summary of a parsed network (debugging).

        Args:
            network: The network to display.
        """
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

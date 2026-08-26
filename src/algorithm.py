from src.classes import Zone, MapDict
from src.error import PathError
from pydantic import BaseModel


class PathFinder(BaseModel):
    map: MapDict

    def dijkstra(self) -> list[str]:
        start, end = None, None
        for zone in self.map["zones"]:
            if zone.kind == 1:
                start = zone
            if zone.kind == -1:
                end = zone
        if not start:
            raise PathError("Map does not have a start hub defined, aborting.")
        if not end:
            raise PathError("Map does not have a goal hub defined, aborting.")

        turns = 0
        current = start
        path = []
        while current != end:
            path.append(current.name)
            next = self._find_best_connection(current)
            turns += self._get_cost(next)
            current = next
        path.append(end.name)
        return path

    def _find_connections(self, zone: Zone) -> list[tuple[Zone, int]]:
        connections = []
        for connection in self.map["connections"]:
            neighbor = connection.other(zone)
            if neighbor is not None:
                cost = self._get_cost(neighbor)
                if cost == -1:
                    continue
                else:
                    connections.append((neighbor, cost))
        return connections

    def _find_best_connection(self, zone: Zone) -> Zone:
        connections = self._find_connections(zone)
        cost = 5
        names: list[Zone] = []
        for connection in connections:
            if connection[1] < cost:
                cost = connection[1]
                names.insert(0, connection[0])
            else:
                names.append(connection[0])
        for i in range(len(names)):
            for j in range(1, len(names)):
                if names[j].zone_type == "priority":
                    names[i], names[j] = names[j], names[i]
        return names[0]

    @staticmethod
    def _get_cost(zone: Zone) -> int:
        if zone.zone_type == "normal":
            return 1
        if zone.zone_type == "restricted":
            return 2
        if zone.zone_type == "priority":
            return 1
        else:
            return -1

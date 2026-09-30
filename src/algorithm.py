from src.classes import Network
from src.error import PathError
from pydantic import BaseModel
from heapq import heapify, heappop, heappush


class PathFinder(BaseModel):
    """Finds the cheapest route from the start hub to the end hub.

    Attributes:
        map: The parsed network to search.
        graph: Adjacency map of zone name -> {neighbor name: entry cost},
            built by ``_create_graph`` with blocked zones left out.
    """
    map: Network
    graph: dict[str, dict[str, int]] = {}

    def _create_graph(self) -> None:
        """Build ``self.graph`` from the network's zones and connections.

        Blocked zones are excluded both as nodes and as neighbors. Edge
        weights are the cost of entering the neighbor zone.
        """
        graph = {}
        for zone in self.map.zones:
            if zone.zone_type == "blocked":
                continue
            neighbors = {}
            for connection in self.map.connections:
                next = connection.other(zone)
                if next is not None:
                    if next.zone_type == "blocked":
                        continue
                    neighbors[next.name] = next.cost
                graph[zone.name] = neighbors
        self.graph = graph

    def print_graph(self) -> None:
        """Print the adjacency map, one zone per line (debugging)"""
        print("{")
        for k, v in self.graph.items():
            print(f"'{k}': {v}")
        print("}")

    @property
    def get_graph(self) -> dict[str, dict[str, int]]:
        """dict[str, dict[str, int]]: current adjacency map"""
        return self.graph

    def dijkstra(self) -> dict[str, float]:
        """Compute the cheapest cost from the start hub to every zone.

        Returns:
            Mapping of zone name to its minimal cost from the start hub;
            unreachable zones keep path cost of infinity.

        Raises:
            PathError: If the map has no start or end hub, or if the end
                hub is unreachable.
        """
        start, end = None, None
        for zone in self.map.zones:
            if zone.kind == 1:
                start = zone.name
            if zone.kind == -1:
                end = zone.name
        if not start:
            raise PathError(
                f"Map '{self.map.name}' does not have a start hub defined,\
aborting."
            )
        if not end:
            raise PathError(
                f"Map '{self.map.name}' does not have a goal hub defined,\
aborting."
            )
        distances = {hub: float("inf") for hub in self.graph}
        distances[start] = 0

        pq = [(0, start)]
        heapify(pq)
        visited = set()

        while pq:
            current_cost, current_hub = heappop(pq)

            if current_hub in visited:
                continue
            visited.add(current_hub)

            for neighbor, cost in self.graph[current_hub].items():
                if neighbor not in distances:
                    continue
                new_cost = current_cost + cost
                if new_cost < distances[neighbor]:
                    distances[neighbor] = new_cost
                    heappush(pq, (new_cost, neighbor))

        if distances[end] == float("inf"):
            raise PathError(
                f"Goal hub '{end}' is not reachable from start in \
'{self.map.name}'."
            )
        return distances

    def run(self) -> list[tuple[str, int]]:
        """Build the graph, run Dijkstra and reconstruct one cheapest path.

        Returns:
            The path from start to end as (zone name, cost to enter) pairs;
            the first entry is the start hub with cost 0.

        Raises:
            PathError: If the map has no end hub or it is unreachable.
        """
        self._create_graph()
        distances = self.dijkstra()
        came_from = {hub: "" for hub in self.graph}

        for hub, cost in distances.items():
            for neighbor, c in self.graph[hub].items():
                if distances[neighbor] == cost + c:
                    came_from[neighbor] = hub

        path = []
        target = None
        for zone in self.map.zones:
            if zone.kind == -1:
                target = zone.name
        if not target:
            raise PathError("Map does not have a goal hub defined, aborting.")
        current = target
        while current != "":
            path.append(current)
            current = came_from[current]
        path.reverse()
        cost = 0
        path_cost = [(path[0], 0)]
        for i in range(len(path) - 1):
            cost = self.graph[path[i]][path[i + 1]]
            path_cost.append((path[i + 1], cost))
        return path_cost

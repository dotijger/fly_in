from src.parser import Parser
from src.algorithm import PathFinder
from src.error import ParseError, PathError
from pathlib import Path
import sys

if __name__ == "__main__":
    parse = Parser(input=Path("maps"))
    try:
        maps = parse._import_maps()
        for map in maps:
            parse.print(map)
            pathfinder = PathFinder(map=map)
            print(pathfinder.dijkstra())
    except (ParseError, ValueError, PathError) as e:
        print(e)
        sys.exit(1)

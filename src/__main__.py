from src.parser import Parser
from src.logger import Logger
from src.simulation import Simulation
from src.algorithm import PathFinder
from src.error import ParseError, PathError
from pathlib import Path
import sys

if __name__ == "__main__":
    parse = Parser(input=Path("maps"))
    try:
        logger = Logger()
        maps = parse._import_maps()
        for map in maps:
            print("\n")
            print(f"Running simulation on map: '{map['map_name']}'")
            print("\nImported map information: \n")
            parse.print(map)
            sim = Simulation(map=map, logger=logger)
            sim.run()
    except (ParseError, ValueError, PathError) as e:
        print(e)
        sys.exit(1)

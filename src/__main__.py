from src.parser import Parser
from src.logger import Logger
from src.simulation import Simulation
from src.visual import Visualizer
from src.error import ParseError, PathError, SimulationError
from pathlib import Path
import sys

if __name__ == "__main__":
    parse = Parser(input=Path("maps"))
    try:
        logger = Logger()
        maps = parse._import_maps()
        sims = []
        for map in maps:
            sim = Simulation(map=map, logger=logger)
            sim.run()
            sims.append(sim)
        vis = Visualizer(sims=sims)
        vis.run()
    except (ParseError, ValueError, PathError, SimulationError) as e:
        print(e)
        sys.exit(1)

        # for map in maps:
        # print("\n")
        #   print(f"Running simulation on map: '{map.name}'")
        #    print("\nImported map information: \n")
        #    parse.print(map)
        #   sim = Simulation(map=map, logger=logger)
        #   sim.run()

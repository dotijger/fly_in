from pathlib import Path
from src.classes import Zone, Connection, Simulation
import argparse


class Parser(BaseModel):
    input: Path

    def _import_maps(self) -> None:
        
    def _read_map(self) -> None:
        with open(input, r) as map:
            for line in map:
                if line.startswith('nb_drones: '):

                if line.startswith("#"):
                    continue
                if line.startswith("zone:"):
                    ...
                if line.startswith("connection:"):
                    ...
                if len(line) == 0:
                    continue
                else:
                    raise ParseError(f"Unexpected line in map: {line}")

import curses
from pydantic import BaseModel
from src.simulation import Simulation
from src.logger import Logger
from src.classes import Record, Network
from src.error import VisualizationError
from enum import Enum, auto


class Screen(Enum):
    MENU = auto()
    MAP_SELECT = auto()
    VIEWER = auto()
    QUIT = auto()


class Visualizer(BaseModel):
    sims: list[Simulation]
    selected_map: Simulation | None = None
    map: list[Network] = []
    COLOR_MAP: dict[str, tuple[int, int]] = {}
    DEFAULT_COLOR: tuple[int, int] = (0, 0)

    def run_visualization(self, stdscr: curses.window) -> None:
        curses.curs_set(0)
        self.init_colors()
        screen = Screen.MENU

        while screen != Screen.QUIT:
            if screen == Screen.MENU:
                screen = self.draw_menu(stdscr)
            elif screen == Screen.MAP_SELECT:
                screen = self.draw_map_select(stdscr)
            elif screen == Screen.VIEWER:
                if self.selected_map is None:
                    raise VisualizationError(
                        "No map has been selected, unable to start visualization."
                    )
                turn_records: list[Record] = self.selected_map.log
                screen = self.draw_viewer(
                    stdscr, self.selected_map.map, turn_records
                )

    def run(self) -> None:
        curses.wrapper(self.run_visualization)

    def init_colors(self) -> None:
        curses.start_color()
        curses.use_default_colors()

        self.COLOR_MAP: dict[str, tuple[int, int]] = {
            "green": (curses.COLOR_GREEN, curses.A_NORMAL),
            "red": (curses.COLOR_RED, curses.A_NORMAL),
            "blue": (curses.COLOR_BLUE, curses.A_NORMAL),
            "yellow": (curses.COLOR_YELLOW, curses.A_NORMAL),
            "cyan": (curses.COLOR_CYAN, curses.A_NORMAL),
            "magenta": (curses.COLOR_MAGENTA, curses.A_NORMAL),
            "gray": (curses.COLOR_WHITE, curses.A_NORMAL),
            "black": (
                curses.COLOR_WHITE,
                curses.A_DIM,
            ),  # black text is invisible on black bg, so proxy it
            # bucketed into nearest base + bold/dim to distinguish
            "orange": (curses.COLOR_YELLOW, curses.A_BOLD),
            "gold": (curses.COLOR_YELLOW, curses.A_DIM),
            "purple": (curses.COLOR_MAGENTA, curses.A_DIM),
            "violet": (curses.COLOR_MAGENTA, curses.A_BOLD),
            "brown": (curses.COLOR_RED, curses.A_DIM),
            "maroon": (curses.COLOR_RED, curses.A_DIM),
            "darkred": (curses.COLOR_RED, curses.A_BOLD),
            "crimson": (curses.COLOR_RED, curses.A_BOLD),
            "lime": (curses.COLOR_GREEN, curses.A_BOLD),
            "rainbow": (
                curses.COLOR_WHITE,
                curses.A_BOLD,
            ),  # goal zone in challenger map — no way to actually rainbow a single addstr call
        }

        self.DEFAULT_COLOR = (curses.COLOR_WHITE, curses.A_NORMAL)

    def draw_menu(self, stdscr: curses.window) -> Screen:
        options = ["start", "quit"]
        selected = 0

        while True:
            stdscr.erase()
            stdscr.addstr(1, 2, "fly-in by odschreu")
            for i, label in enumerate(options):
                attribute = (
                    curses.A_REVERSE if i == selected else curses.A_NORMAL
                )
                stdscr.addstr(3 + i, 4, f"[ {label} ]", attribute)
            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP:
                selected = (selected - 1) % len(options)
            elif key == curses.KEY_DOWN:
                selected = (selected + 1) % len(options)
            elif key in (curses.KEY_ENTER, 10, 13):
                return Screen.MAP_SELECT if selected == 0 else Screen.QUIT

    def draw_map_select(self, stdscr: curses.window) -> Screen:
        map_options = []
        map_name = {}
        for i, sim in enumerate(self.sims):
            map_options.append(sim.map.name)
            map_name[i] = sim
        map_options.append("quit")
        selected = 0
        while True:
            stdscr.erase()
            stdscr.addstr(1, 2, "please select a map:")
            for i, label in enumerate(map_options):
                attribute = (
                    curses.A_REVERSE if i == selected else curses.A_NORMAL
                )
                stdscr.addstr(3 + i, 4, f"[ '{label}' ]", attribute)
            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP:
                selected = (selected - 1) % len(map_options)
            elif key == curses.KEY_DOWN:
                selected = (selected + 1) % len(map_options)
            elif key in (curses.KEY_ENTER, 10, 13):
                if selected != len(map_options) - 1:
                    self.selected_map = map_name[selected]
                return (
                    Screen.VIEWER
                    if selected != len(map_options) - 1
                    else Screen.QUIT
                )

    def draw_viewer(
        self, stdscr: curses.window, map: Network, turns: list[Record]
    ) -> Screen:
        id = 0
        max_id = len(turns) - 1

        while True:
            stdscr.erase()
            self.draw_network(stdscr, map)
            # self.draw_drones(stdscr, turns[id])
            # self.draw_status_bar(stdscr, id, max_id)
            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_RIGHT:
                id = min(id + 1, max_id)
            elif key == curses.KEY_LEFT:
                id = max(id - 1, 0)
            elif key == ord("q"):
                return Screen.MENU

    @staticmethod
    def compute_drawing_scale(
        stdscr: curses.window, map: Network
    ) -> tuple[float, float, int, int, int, int]:
        screen_height, screen_width = stdscr.getmaxyx()
        xs = [z.x for z in map.zones]
        ys = [z.y for z in map.zones]
        max_x, min_x = max(xs), min(xs)
        max_y, min_y = max(ys), min(ys)

        margin_top, margin_bottom = 4, 4
        usable_width = screen_width - 4
        usable_height = screen_height - margin_top - margin_bottom

        use_x = max(max_x - min_x, 1)
        use_y = max(max_y - min_y, 1)

        scale_x = usable_width / use_x
        scale_y = usable_height / use_y

        return scale_x, scale_y, min_x, max_x, min_y, max_y

    @staticmethod
    def convert_to_screen(
        x: int, y: int, scale_x: float, scale_y: float, min_x: int, max_y: int
    ) -> tuple[int, int]:
        col = int((x - min_x) * scale_x) + 4
        row = int((max_y - y) * scale_y) + 4
        return row, col

    # addstr(row, col, text, attribute) (row = y, col = x)
    def draw_network(self, stdscr: curses.window, map: Network) -> None:
        scale_x, scale_y, min_x, max_x, min_y, max_y = (
            self.compute_drawing_scale(stdscr, map)
        )

        center = int((max_x - min_x) / 2)
        color, _ = self.DEFAULT_COLOR
        stdscr.addstr(1, center, f"{map.name}", color | curses.A_UNDERLINE)
        for z in map.zones:
            y, x = self.convert_to_screen(
                z.x, z.y, scale_x, scale_y, min_x, max_y
            )
            if z.color is None:
                color, attribute = self.DEFAULT_COLOR
            else:
                color, attribute = self.COLOR_MAP.get(
                    z.color, self.DEFAULT_COLOR
                )
            try:
                stdscr.addstr(y, x, f"{z.name}", color | attribute)
            except curses.error:
                continue

        for c in map.connections:
            pass

    def draw_drones(self, stdscr: curses.window, turn: Record) -> None:
        pass

    def draw_status_bar(
        self, stdscr: curses.window, turn_id: int, turn_total: int
    ) -> None:
        pass


if __name__ == "__main__":
    log = Logger()
    vis = Visualizer()
    vis.run()

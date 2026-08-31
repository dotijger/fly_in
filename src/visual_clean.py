import curses
from src.simulation import Simulation
from src.logger import Logger
from src.classes import Record, Network, Zone
from src.error import VisualizationError
from enum import Enum, auto
from collections import deque
from typing import Deque, Self


class Screen(Enum):
    MENU = auto()
    MAP_SELECT = auto()
    VIEWER = auto()
    QUIT = auto()


class Visualizer:
    def __init__(
        self, sims: list[Simulation], selected_map: Simulation | None = None
    ) -> None:
        self.sims = sims
        self.selected_map = selected_map
        self.map: list[Network] = []
        self.COLOR_MAP: dict[str, tuple[int, int]] = {}
        self.DEFAULT_COLOR: tuple[int, int] = (0, 0)
        self.DIRECTION_STEP = {
            "up": (-1, 0),
            "down": (1, 0),
            "left": (0, -1),
            "right": (0, 1),
        }
        self.STACK_AXIS = {
            "up": "x",
            "down": "x",
            "left": "y",
            "right": "y",
        }

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
                    stdscr, self.selected_map.map, turn_records, self
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

        unique_combos: dict[int, int] = {}
        self.PAIR_MAP: dict[str, int] = {}

        next_pair_id = 1
        for name, (color, attr) in self.COLOR_MAP.items():
            if color not in unique_combos:
                curses.init_pair(next_pair_id, color, -1)
                unique_combos[color] = next_pair_id
                next_pair_id += 1
            self.PAIR_MAP[name] = unique_combos[color]

    def get_colors(self, color: str) -> tuple[int, int]:
        _, attr = self.COLOR_MAP.get(color, self.DEFAULT_COLOR)
        pair_id = self.PAIR_MAP[color]
        return (pair_id, attr)

    # at draw time:
    # color, attr = self.COLOR_MAP.get(color_name, self.DEFAULT_COLOR)
    # pair_id = self.PAIR_MAP[color_name]
    # self.stdscr.addstr(y, x, char, curses.color_pair(pair_id) | attr)

    def draw_menu(self, stdscr: curses.window) -> Screen:
        options = ["quit", "start"]
        selected = 0
        screen_height, screen_width = stdscr.getmaxyx()
        center_y = screen_height // 2
        center_x = screen_width // 2

        while True:
            stdscr.erase()
            title = "fly-in by odschreu"
            title_x = center_x - len(title) // 2
            stdscr.addstr(center_y - 2, title_x, title, curses.A_BOLD)
            for i, label in enumerate(options):
                attribute = (
                    curses.A_REVERSE if i == selected else curses.A_NORMAL
                )
                x = title_x + len(title) // 4
                stdscr.addstr(center_y - i, x, f"[ {label} ]", attribute)
            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP:
                selected = (selected - 1) % len(options)
            elif key == curses.KEY_DOWN:
                selected = (selected + 1) % len(options)
            elif key in (curses.KEY_ENTER, 10, 13):
                return Screen.MAP_SELECT if selected != 0 else Screen.QUIT
            elif key in (27, ord("q")):
                return Screen.QUIT

    def draw_map_select(self, stdscr: curses.window) -> Screen:
        map_options = []
        map_name = {}
        for i, sim in enumerate(self.sims):
            map_options.append(sim.map.name)
            map_name[i] = sim
        map_options.append("quit")
        selected = 0
        screen_height, screen_width = stdscr.getmaxyx()
        center_y = screen_height // 2
        center_x = screen_width // 2

        start_y = center_y - (len(map_options) + 2) // 2

        while True:
            stdscr.erase()
            title = "PLEASE SELECT A MAP:"
            title_x = center_x - len(title) // 3
            stdscr.addstr(start_y, title_x, title, curses.A_BOLD)
            for i, label in enumerate(map_options):
                attribute = (
                    curses.A_REVERSE if i == selected else curses.A_NORMAL
                )
                x = center_x - len(label) // 2
                stdscr.addstr(start_y + 1 + i, x, f"[ '{label}' ]", attribute)
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
            elif key == 27:
                return Screen.QUIT
            elif key == ord("q"):
                return Screen.MENU

    def draw_viewer(
        self,
        stdscr: curses.window,
        map: Network,
        turns: list[Record],
        vis: Self,
    ) -> Screen:
        id = 0
        max_id = len(turns) - 1
        height, width = stdscr.getmaxyx()
        map_width = int(width * 0.65)
        log_width = width - map_width

        map_window = curses.newwin(height, map_width, 0, 0)
        log_window = curses.newwin(height, log_width, 0, map_width)

        log_drawer = LogDrawer(log_window, turns)
        map_drawer = MapDrawer(map_window, map, turns, vis)

        log_drawer.render(id)
        map_drawer.render(id)
        curses.doupdate()

        while True:
            key = stdscr.getch()
            if key == curses.KEY_RIGHT:
                id = min(id + 1, max_id)
                log_drawer.render(id)
                map_drawer.render(id)
                curses.doupdate()
            elif key == curses.KEY_LEFT:
                id = max(id - 1, 0)
                log_drawer.render(id)
                map_drawer.render(id)
                curses.doupdate()
            elif key == ord("q"):
                return Screen.MAP_SELECT
            elif key == 27:
                return Screen.QUIT


class LogDrawer:
    def __init__(self, window: curses.window, turns: list[Record]) -> None:
        self._window = window
        self._height, _ = window.getmaxyx()
        self._turns = turns
        self._max_lines = max(self._height - 2, 1)
        self._lines: list[str] = []

    def _append_turn(self, turn_id: int, log: Record) -> None:
        formatted_turn = log.get_records()
        self._lines.append(f"T{turn_id:>2}: {formatted_turn}")

    def _safe_addstr(self, y: int, x: int, text: str, attr: int) -> None:
        max_h, max_w = self._window.getmaxyx()

        if 0 <= y < max_h - 1:
            try:
                self._window.addstr(y, x, text[: max_w - x - 1], attr)
            except curses.error:
                pass

    def render(self, id: int):
        self._window.erase()
        self._window.box()
        self._window.addstr(0, 2, "[ TURN LOG ]", curses.A_BOLD)

        if id != 0:
            self._lines = []
            for i in range(id):
                self._append_turn(i + 1, self._turns[i])
            visible_lines = list(self._lines)
            for i, line in enumerate(visible_lines, start=1):
                attr = (
                    curses.A_BOLD if i == len(visible_lines) else curses.A_DIM
                )
                self._safe_addstr(i, 2, line, attr)

        self._window.noutrefresh()


class MapDrawer:
    def __init__(
        self,
        window: curses.window,
        map: Network,
        turns: list[Record],
        vis: Visualizer,
    ) -> None:
        self._window = window
        self._map = map
        self._vis = vis
        self._zones = {z.name: z for z in map.zones}
        self._connections = map.connections
        self._turns = turns
        self._screen_position: dict[str, tuple[int, int]] = {}
        self.MARGIN = 2
        self._compute_drawing_layout()

    def render(self, turn_id: int) -> None:
        self._window.erase()
        self._window.box()
        self._window.addstr(0, 2, f"[{self._map.name}]", curses.A_BOLD)

        self._draw_network()
        self._draw_drones(turn_id)
        self._draw_status_bar(turn_id)

        self._window.noutrefresh()

    def _draw_status_bar(self, turn_id: int) -> None:
        max_y, max_x = self._window.getmaxyx()
        self._window.addstr(
            max_y - 1,
            max_x - 4,
            f"{turn_id}/{len(self._turns) - 1}",
            curses.A_BOLD,
        )

    def _safe_addch(self, y: int, x: int, char: int) -> None:
        try:
            self._window.addch(y, x, char)
        except curses.error:
            pass

    def _safe_addstr(self, y: int, x: int, text: str, attr: int) -> None:
        try:
            self._window.addstr(y, x, text, attr)
        except curses.error:
            pass

    def _compute_drawing_layout(self) -> None:
        screen_height, screen_width = self._window.getmaxyx()
        xs = [z.x for z in self._map.zones]
        ys = [z.y for z in self._map.zones]
        max_x, min_x = max(xs), min(xs)
        max_y, min_y = max(ys), min(ys)

        usable_width = screen_width - 2 * self.MARGIN
        usable_height = screen_height - 2 * self.MARGIN

        use_x = max(max_x - min_x, 1)
        use_y = max(max_y - min_y, 1)

        for zone in self._zones.values():
            x = (zone.x - min(xs)) / use_x
            y = (zone.y - min(ys)) / use_y
            scaled_x = self.MARGIN + int(x * (usable_width - 1))
            scaled_y = self.MARGIN + int(y * (usable_height - 3))
            self._screen_position[zone.name] = (scaled_y, scaled_x)

    def _draw_line(self, ya: int, xa: int, yb: int, xb: int) -> None:
        self._draw_vertical_line(ya, xa, yb)
        self._draw_horizontal_line(xa, yb, xb)
        self._draw_corner(ya, xa, yb, xb)

    def _draw_vertical_line(self, ya: int, xa: int, yb: int) -> None:
        if ya == yb:
            return
        step = 1 if yb > ya else -1
        for y in range(ya + step, yb, step):
            self._safe_addch(y, xa, curses.ACS_VLINE)

    def _draw_horizontal_line(self, xa: int, yb: int, xb: int) -> None:
        if xa == xb:
            return
        step = 1 if xb > xa else -1
        for x in range(xa + step, xb, step):
            self._safe_addch(yb, x, curses.ACS_HLINE)

    def _draw_corner(self, ya: int, xa: int, yb: int, xb: int) -> None:
        if ya == yb or xa == xb:
            return

        from_above = yb > ya
        right_turn = xb > xa

        if from_above and right_turn:
            char = curses.ACS_LLCORNER
        if not from_above and right_turn:
            char = curses.ACS_ULCORNER
        if from_above and not right_turn:
            char = curses.ACS_LRCORNER
        if not from_above and not right_turn:
            char = curses.ACS_URCORNER

        self._safe_addch(yb, xa, char)

    def _get_connection_direction(self, zone: Zone, other: Zone) -> str:
        zy, zx = zone.y, zone.x
        oy, ox = other.y, other.x
        if oy != zy:
            return "down" if oy > zy else "up"
        return "right" if ox > zx else "left"

    def _draw_ports(self) -> None:
        pass

    # addstr(row, col, text, attribute) (row = y, col = x)
    def _draw_network(self) -> None:
        max_y, max_x = self._window.getmaxyx()
        for c in self._map.connections:
            ya, xa = self._screen_position[c.a.name]
            yb, xb = self._screen_position[c.b.name]
            self._draw_line(ya, xa, yb, xb)
        center = int(max_x / 2)
        self._window.addstr(1, center, f"{self._map.name}", curses.A_UNDERLINE)
        for z in self._map.zones:
            y, x = self._screen_position[z.name]
            if z.color is None:
                id, attr = 0, curses.A_NORMAL
            else:
                id, attr = self._vis.get_colors(z.color)
            self._safe_addstr(y - 1, x, "[hub]", 0 | curses.A_BOLD)
            self._safe_addstr(y, x, f"{z.name}", id | attr)

    def _draw_drones(self, turn_id: int) -> None:
        pass


if __name__ == "__main__":
    log = Logger()
    vis = Visualizer()
    vis.run()

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

    def _safe_addch(
        self, stdscr: curses.window, y: int, x: int, char: int
    ) -> None:
        try:
            stdscr.addch(y, x, char)
        except curses.error:
            pass

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
                return Screen.MAP_SELECT
            elif key == 27:
                return Screen.QUIT

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
        margin_left, margin_right = 4, 10
        usable_width = screen_width - margin_left - margin_right
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

    # parametric interpolation position[i] = start + (end - start) * (i / n)
    def _draw_line_old(
        self, stdscr: curses.window, ya: int, xa: int, yb: int, xb: int
    ) -> None:
        steps = max(abs(xb - xa), abs(yb - ya), 1) // 2
        with open("/tmp/debug.log", "a") as f:
            f.write(
                f"draw_line ya={ya} xa={xa} yb={yb} xb={yb} steps={steps}\n"
            )
        for i in range(1, steps):
            y = ya + (yb - ya) * i // steps
            x = xa + (xb - xa) * i // steps
            try:
                char = (
                    "|"
                    if xa == xb
                    else (
                        "-"
                        if ya == yb
                        else ("\\" if (xb - xa) * (yb - ya) > 0 else "/")
                    )
                )
                stdscr.addstr(y, x, char)
            except curses.error as e:
                with open("/tmp/debug.log", "a") as f:
                    f.write(f" FAILED at y={y} x={x}: {e}\n")
                pass

    def _draw_line(
        self, stdscr: curses.window, ya: int, xa: int, yb: int, xb: int
    ) -> None:
        self._draw_vertical_line(stdscr, ya, xa, yb)
        self._draw_horizontal_line(stdscr, xa, yb, xb)
        self._draw_corner(stdscr, ya, xa, yb, xb)

    def _draw_vertical_line(
        self, stdscr: curses.window, ya: int, xa: int, yb: int
    ) -> None:
        if ya == yb:
            return
        step = 1 if yb > ya else -1
        for y in range(ya + step, yb, step):
            self._safe_addch(stdscr, y, xa, curses.ACS_VLINE)

    def _draw_horizontal_line(
        self, stdscr: curses.window, xa: int, yb: int, xb: int
    ) -> None:
        if xa == xb:
            return
        step = 1 if xb > xa else -1
        for x in range(xa + step, xb, step):
            self._safe_addch(stdscr, yb, x, curses.ACS_HLINE)

    def _draw_corner(
        self, stdscr: curses.window, ya: int, xa: int, yb: int, xb: int
    ) -> None:
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

        self._safe_addch(stdscr, yb, xa, char)

    # addstr(row, col, text, attribute) (row = y, col = x)
    def draw_network(self, stdscr: curses.window, map: Network) -> None:
        scale_x, scale_y, min_x, max_x, min_y, max_y = (
            self.compute_drawing_scale(stdscr, map)
        )

        for c in map.connections:
            ya, xa = self.convert_to_screen(
                c.a.x, c.a.y, scale_x, scale_y, min_x, max_y
            )
            yb, xb = self.convert_to_screen(
                c.b.x, c.b.y, scale_x, scale_y, min_x, max_y
            )
            self._draw_line(stdscr, ya, xa, yb, xb)
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
                stdscr.addstr(
                    y - 1, x, "[hub]", curses.COLOR_WHITE | curses.A_BOLD
                )
                stdscr.addstr(y, x, f"{z.name}", color | attribute)
            except curses.error:
                continue

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

"""Demo: split-pane curses viewer (map panel + turn log panel).

This is a STANDALONE skeleton with fake data to show the windowing,
scaling, and refresh pattern. It is NOT wired to your parser or
TurnResolver — swap `DEMO_ZONES` / `DEMO_CONNECTIONS` / `DEMO_TURNS`
for your real domain objects and this structure should drop in
directly under your VIEWER state.

Controls: SPACE = advance one turn, q = quit.
"""

from __future__ import annotations

import curses
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, TYPE_CHECKING

if TYPE_CHECKING:
    from _curses import window as CursesWindow
else:
    CursesWindow = object


# --------------------------------------------------------------------------
# Minimal stand-ins for your real domain model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ZoneView:
    """Everything the renderer needs to know about a zone."""

    name: str
    x: int
    y: int
    zone_type: str  # "normal" | "restricted" | "priority" | "blocked" | "start" | "end"


@dataclass(frozen=True)
class ConnectionView:
    """A bidirectional edge between two zone names."""

    zone_a: str
    zone_b: str


# Fake map: replace with your parsed Zone/Connection objects.
DEMO_ZONES: list[ZoneView] = [
    ZoneView("start", 0, 2, "start"),
    ZoneView("roof1", 3, 4, "restricted"),
    ZoneView("roof2", 6, 2, "normal"),
    ZoneView("corridorA", 4, 3, "priority"),
    ZoneView("tunnelB", 7, 4, "normal"),
    ZoneView("obstacleX", 5, 5, "blocked"),
    ZoneView("goal", 10, 0, "end"),
]

DEMO_CONNECTIONS: list[ConnectionView] = [
    ConnectionView("start", "roof1"),
    ConnectionView("start", "corridorA"),
    ConnectionView("roof1", "roof2"),
    ConnectionView("roof2", "goal"),
    ConnectionView("corridorA", "tunnelB"),
    ConnectionView("tunnelB", "goal"),
]

# Fake per-turn drone positions: turn -> {drone_id: zone_name}.
# In your real code this comes from TurnResolver.resolve() history.
DEMO_TURNS: list[dict[int, str]] = [
    {1: "roof1", 2: "corridorA"},
    {1: "roof2", 2: "tunnelB"},
    {1: "goal", 2: "goal"},
]

ZONE_COLOR_PAIR = {
    "normal": 1,
    "restricted": 2,
    "priority": 3,
    "blocked": 4,
    "start": 5,
    "end": 6,
}


# --------------------------------------------------------------------------
# Map panel
# --------------------------------------------------------------------------


class MapPanel:
    """Owns the curses window that draws zones, connections, and drones."""

    MARGIN = 2  # cells of padding inside the border, per side

    def __init__(
        self,
        window: CursesWindow,
        zones: list[ZoneView],
        connections: list[ConnectionView],
    ) -> None:
        self._window = window
        self._zones = {z.name: z for z in zones}
        self._connections = connections
        self._screen_pos: dict[str, tuple[int, int]] = {}
        self._compute_layout()

    def _compute_layout(self) -> None:
        """Scale zone (x, y) into screen coordinates that fit the window."""
        height, width = self._window.getmaxyx()
        usable_h = max(height - 2 * self.MARGIN, 1)
        usable_w = max(width - 2 * self.MARGIN, 1)

        xs = [z.x for z in self._zones.values()]
        ys = [z.y for z in self._zones.values()]
        span_x = max(xs) - min(xs) or 1  # avoid div by zero on 1-node maps
        span_y = max(ys) - min(ys) or 1

        for zone in self._zones.values():
            norm_x = (zone.x - min(xs)) / span_x
            norm_y = (zone.y - min(ys)) / span_y
            screen_x = self.MARGIN + int(norm_x * (usable_w - 1))
            # leave a blank row under every node for its label
            screen_y = self.MARGIN + int(norm_y * (usable_h - 3))
            self._screen_pos[zone.name] = (screen_y, screen_x)

    def render(self, drone_positions: dict[int, str]) -> None:
        """Redraw the full map panel for the current turn's drone positions."""
        self._window.erase()
        self._window.box()
        self._window.addstr(0, 2, " map ", curses.A_BOLD)

        self._draw_connections()
        self._draw_zones(drone_positions)

        self._window.noutrefresh()

    def _draw_connections(self) -> None:
        for conn in self._connections:
            y1, x1 = self._screen_pos[conn.zone_a]
            y2, x2 = self._screen_pos[conn.zone_b]
            self._draw_line(y1, x1, y2, x2)

    def _draw_line(self, y1: int, x1: int, y2: int, x2: int) -> None:
        """Bresenham-ish line using '.' so it never obscures zone glyphs
        (zones are drawn afterwards, on top)."""
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        x, y = x1, y1
        max_h, max_w = self._window.getmaxyx()
        while (x, y) != (x2, y2):
            if 0 < y < max_h - 1 and 0 < x < max_w - 1:
                try:
                    self._window.addch(y, x, curses.ACS_CKBOARD)
                except curses.error:
                    pass  # writing to the bottom-right cell can raise; ignore
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def _draw_zones(self, drone_positions: dict[int, str]) -> None:
        # invert drone_positions -> zone_name: [drone_ids]
        occupants: dict[str, list[int]] = {}
        for drone_id, zone_name in drone_positions.items():
            occupants.setdefault(zone_name, []).append(drone_id)

        for name, (y, x) in self._screen_pos.items():
            zone = self._zones[name]
            color = curses.color_pair(ZONE_COLOR_PAIR.get(zone.zone_type, 1))
            here = occupants.get(name, [])

            if here:
                glyph = str(here[0])[-1]  # single-digit display
                attr = color | curses.A_BOLD | curses.A_REVERSE
                if len(here) > 1:
                    attr |= curses.A_UNDERLINE  # signal "more than one here"
            else:
                glyph_map = {
                    "normal": ".",
                    "restricted": "R",
                    "priority": "P",
                    "blocked": "#",
                    "start": "S",
                    "end": "E",
                }
                glyph = glyph_map[zone.zone_type]
                attr = color

            self._safe_addstr(y, x, glyph, attr)
            # small label under the node, truncated to keep things compact
            label = name[:8]
            label_attr = curses.color_pair(0) | curses.A_DIM
            self._safe_addstr(
                y + 1, max(x - len(label) // 2, 0), label, label_attr
            )

    def _safe_addstr(self, y: int, x: int, text: str, attr: int) -> None:
        max_h, max_w = self._window.getmaxyx()
        if 0 <= y < max_h - 1 and 0 <= x < max_w - 1:
            try:
                self._window.addstr(y, x, text[: max_w - x - 1], attr)
            except curses.error:
                pass  # bottom-right corner write; safe to ignore


# --------------------------------------------------------------------------
# Log panel
# --------------------------------------------------------------------------


class LogPanel:
    """Owns the curses window that shows a scrolling per-turn move log."""

    def __init__(self, window: CursesWindow) -> None:
        self._window = window
        height, _ = window.getmaxyx()
        self._max_lines = max(height - 2, 1)
        self._lines: Deque[str] = deque(
            maxlen=200
        )  # keep history for scroll-back later

    def append_turn(self, turn_number: int, moves: dict[int, str]) -> None:
        formatted = " ".join(
            f"D{drone_id}-{zone}" for drone_id, zone in moves.items()
        )
        self._lines.append(f"Turn {turn_number:>3}: {formatted}")

    def render(self) -> None:
        self._window.erase()
        self._window.box()
        self._window.addstr(0, 2, " log ", curses.A_BOLD)

        visible = list(self._lines)[-self._max_lines :]
        for i, line in enumerate(visible, start=1):
            attr = curses.A_BOLD if i == len(visible) else curses.A_NORMAL
            self._safe_addstr(i, 2, line, attr)

        self._window.noutrefresh()

    def _safe_addstr(self, y: int, x: int, text: str, attr: int) -> None:
        max_h, max_w = self._window.getmaxyx()
        if 0 <= y < max_h - 1:
            try:
                self._window.addstr(y, x, text[: max_w - x - 1], attr)
            except curses.error:
                pass


# --------------------------------------------------------------------------
# Viewer: composes both panels, owns the turn-stepping loop
# --------------------------------------------------------------------------


@dataclass
class ViewerScreen:
    """The VIEWER state: wires MapPanel + LogPanel together."""

    zones: list[ZoneView]
    connections: list[ConnectionView]
    turns: list[dict[int, str]]
    current_turn: int = field(default=0)

    def run(self, stdscr: CursesWindow) -> None:
        curses.curs_set(0)
        self._init_colors()

        height, width = stdscr.getmaxyx()
        map_width = int(width * 0.62)
        log_width = width - map_width

        map_win = curses.newwin(height, map_width, 0, 0)
        log_win = curses.newwin(height, log_width, 0, map_width)

        map_panel = MapPanel(map_win, self.zones, self.connections)
        log_panel = LogPanel(log_win)

        drone_positions: dict[int, str] = {}
        map_panel.render(drone_positions)
        log_panel.render()
        curses.doupdate()

        while True:
            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                break
            if key == ord(" ") and self.current_turn < len(self.turns):
                moves = self.turns[self.current_turn]
                drone_positions.update(moves)
                self.current_turn += 1
                log_panel.append_turn(self.current_turn, moves)

                map_panel.render(drone_positions)
                log_panel.render()
                curses.doupdate()

    @staticmethod
    def _init_colors() -> None:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, -1)  # normal
        curses.init_pair(2, curses.COLOR_RED, -1)  # restricted
        curses.init_pair(3, curses.COLOR_GREEN, -1)  # priority
        curses.init_pair(4, curses.COLOR_BLACK, -1)  # blocked
        curses.init_pair(5, curses.COLOR_GREEN, -1)  # start
        curses.init_pair(6, curses.COLOR_YELLOW, -1)  # end


def main(stdscr: CursesWindow) -> None:
    viewer = ViewerScreen(
        zones=DEMO_ZONES, connections=DEMO_CONNECTIONS, turns=DEMO_TURNS
    )
    viewer.run(stdscr)


if __name__ == "__main__":
    curses.wrapper(main)

#!/usr/bin/env python3
"""Render Vellum's specimen cards: syntax highlighting and a terminal session.

Everything here comes from the theme's own data — `vellum/colors.toml` for the
palette and the syntax roles Omarchy generates from it, `vellum/foot.ini` for
the sixteen terminal slots — so a palette edit moves the pictures with it.
Contrast figures are computed, not typed in.

Usage: `python3 tools/specimens.py [syntax|terminal]` (no argument: both).
"""

from __future__ import annotations

import configparser
import html
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "vellum"
OUT = ROOT / "screenshots"
WALL = ROOT / "tools" / "backgrounds-src" / "0-dawn.svg"

# Card: 1200x780 CSS px, rendered at 2x. Type is 18px, so the screenshots stay
# readable when GitHub scales them down to a README column.
W, H = 1200, 780
WIN_X, WIN_Y, WIN_W, WIN_H = 70, 60, 1060, 660
HEADER = 40
PAD = 40
CONTENT_TOP = WIN_Y + HEADER
CONTENT_H = WIN_H - HEADER

MONO = "JetBrains Mono"
UI = "Noto Sans"

CODE_SIZE, CODE_LH = 18, 29
CODE_ADV = CODE_SIZE * 0.6
CODE_MAX_COLS = 55
CODE_X = WIN_X + PAD + 52
GUTTER = WIN_X + PAD + 40

PANEL_X, PANEL_W = 800, 290
STATUS_H = 32
CHIP_COLS = int((WIN_W - 2 * PAD - (CODE_X - WIN_X)) / CODE_ADV)


# --- palette ---------------------------------------------------------------


def load_colors() -> dict[str, str]:
    return tomllib.loads((THEME / "colors.toml").read_text())


def load_shell() -> dict[str, dict[str, object]]:
    return tomllib.loads((THEME / "shell.toml").read_text())


def mix(front: str, back: str, alpha: float) -> str:
    f, b = rgb(front), rgb(back)
    return "#%02x%02x%02x" % tuple(round(b[i] * (1 - alpha) + f[i] * alpha) for i in range(3))


def load_foot() -> dict[str, str]:
    parser = configparser.ConfigParser()
    parser.read_string((THEME / "foot.ini").read_text())
    return dict(parser["colors-light"])


def rgb(hexcode: str) -> tuple[int, int, int]:
    h = hexcode.lstrip("#")[-6:]
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    r, g, b = (_channel(v) for v in rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(front: str, back: str) -> float:
    hi, lo = sorted((luminance(front), luminance(back)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def ratio(front: str, back: str) -> str:
    return f"{contrast(front, back):.1f}:1"


# --- svg helpers -----------------------------------------------------------


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def text(
    x: float,
    y: float,
    body: str,
    fill: str,
    size: float = CODE_SIZE,
    *,
    family: str = MONO,
    italic: bool = False,
    weight: int = 400,
    anchor: str = "start",
    tracking: float | None = None,
) -> str:
    attrs = [
        f'x="{x:.1f}"',
        f'y="{y:.1f}"',
        f'font-family="{family}"',
        f'font-size="{size}"',
        f'fill="{fill}"',
    ]
    if italic:
        attrs.append('font-style="italic"')
    if weight != 400:
        attrs.append(f'font-weight="{weight}"')
    if anchor != "start":
        attrs.append(f'text-anchor="{anchor}"')
    if tracking is not None:
        attrs.append(f'letter-spacing="{tracking}"')
    return f"<text {' '.join(attrs)}>{esc(body)}</text>"


def label(x: float, y: float, body: str, fill: str, size: float = 10.5) -> str:
    return text(x, y, body, fill, size, family=UI, tracking=1.7, weight=600)


def spans_line(
    x: float,
    y: float,
    spans: list[tuple[str, str]],
    ink: dict[str, tuple[str, bool]],
    size: float = CODE_SIZE,
    limit: int = CODE_MAX_COLS,
) -> str:
    """Draw monospace spans left to right on a fixed character grid."""
    out, col = [], 0
    for body, role in spans:
        if not body:
            continue
        color, italic = ink[role]
        out.append(text(x + col * size * 0.6, y, body, color, size, italic=italic))
        col += len(body)
    if col > limit:
        raise ValueError(f"line overflows {limit} cols ({col}): {spans!r}")
    return "".join(out)


def pad(spans: list[tuple[str, str]], col: int) -> list[tuple[str, str]]:
    used = sum(len(body) for body, _ in spans)
    if used < col:
        spans.append((" " * (col - used), "ink"))
    return spans


# --- syntax roles ----------------------------------------------------------
#
# Mirrors the mapping Omarchy's generator writes for Aether/Neovim and for the
# VS Code theme: keywords take bright plum, functions indigo, types ochre,
# strings moss, numbers clay, comments muted italic, parameters teal.


def syntax_ink(colors: dict[str, str]) -> dict[str, tuple[str, bool]]:
    return {
        "ink": (colors["foreground"], False),
        "kw": (colors["bright_magenta"], False),
        "imp": (colors["blue"], False),
        "fn": (colors["blue"], False),
        "fnlib": (colors["cyan"], False),
        "type": (colors["yellow"], False),
        "str": (colors["green"], False),
        "num": (colors["orange"], False),
        "const": (colors["bright_yellow"], False),
        "param": (colors["cyan"], True),
        "comment": (colors["muted"], True),
        "op": (colors["bright_blue"], False),
    }


SNIPPET: list[list[tuple[str, str]]] = [
    [("from ", "imp"), ("dataclasses", "ink"), (" import ", "imp"), ("dataclass", "fn")],
    [("from ", "imp"), ("pathlib", "ink"), (" import ", "imp"), ("Path", "type")],
    [],
    pad(
        [
            ("PAPER", "const"),
            (" = ", "op"),
            ('"#f7f3ea"', "str"),
        ],
        24,
    )
    + [("# ink 9.5:1, no glare", "comment")],
    [
        ("@", "fn"),
        ("dataclass", "fn"),
        ("(", "ink"),
        ("frozen", "param"),
        ("=", "op"),
        ("True", "num"),
        (")", "ink"),
    ],
    [("class ", "kw"), ("Sheet", "type"), (":", "ink")],
    [('    """One leaf: ink, grain, and the light."""', "str")],
    [("    ", "ink"), ("name", "param"), (": ", "op"), ("str", "ink")],
    [
        ("    ", "ink"),
        ("ink", "param"),
        (": ", "op"),
        ("str", "ink"),
        (" = ", "op"),
        ('"#423f36"', "str"),
    ],
    [],
    [
        ("    def ", "kw"),
        ("mix", "fn"),
        ("(", "ink"),
        ("self", "param"),
        (", ", "ink"),
        ("other", "param"),
        (": ", "op"),
        ('"Sheet"', "str"),
        (", ", "ink"),
        ("t", "param"),
        (": ", "op"),
        ("float", "ink"),
        (")", "ink"),
        (" -> ", "op"),
        ("str", "ink"),
        (":", "ink"),
    ],
    [('        """Ease paper into paper."""', "str")],
    [
        ("        ", "ink"),
        ("return ", "kw"),
        ('""', "str"),
        (".", "op"),
        ("join", "fn"),
        ("(", "ink"),
        ("...", "ink"),
        (")", "ink"),
    ],
    [],
    [
        ("def ", "kw"),
        ("load", "fn"),
        ("(", "ink"),
        ("root", "param"),
        (": ", "op"),
        ("Path", "type"),
        (")", "ink"),
        (" -> ", "op"),
        ("list", "ink"),
        ("[", "ink"),
        ("Sheet", "type"),
        ("]", "ink"),
        (":", "ink"),
    ],
    [
        ("    ", "ink"),
        ("return ", "kw"),
        ("[", "ink"),
        ("Sheet", "type"),
        ("(", "ink"),
        ("p", "param"),
        (".", "op"),
        ("stem", "param"),
        (")", "ink"),
        (" for ", "kw"),
        ("p", "param"),
        (" in ", "kw"),
        ("root", "param"),
        (".", "op"),
        ("glob", "fn"),
        ("(", "ink"),
        ('"*"', "str"),
        (")", "ink"),
        ("]", "ink"),
    ],
    [],
    [
        ("for ", "kw"),
        ("i", "param"),
        (", ", "ink"),
        ("sheet", "param"),
        (" in ", "kw"),
        ("enumerate", "fnlib"),
        ("(", "ink"),
        ("load", "fn"),
        ("(", "ink"),
        ("Path", "type"),
        ("(", "ink"),
        ('"vellum"', "str"),
        (")", "ink"),
        (")", "ink"),
        (")", "ink"),
        (":", "ink"),
    ],
    [
        ("    ", "ink"),
        ("print", "fnlib"),
        ("(", "ink"),
        ('f"{i:02d}  {sheet.name}"', "str"),
        (")", "ink"),
    ],
]


# --- terminal session ------------------------------------------------------

SELECTED = "selected"


def terminal_ink(colors: dict[str, str]) -> dict[str, tuple[str, bool]]:
    return {
        "ink": (colors["foreground"], False),
        "accent": (colors["accent"], False),
        "muted": (colors["muted"], False),
        "subdued": (colors["dark_foreground"], False),
        "red": (colors["red"], False),
        "clay": (colors["orange"], False),
        "ochre": (colors["bright_yellow"], False),
        "green": (colors["green"], False),
        "blue": (colors["blue"], False),
        "num": (colors["orange"], False),
        SELECTED: (colors["selection_foreground"], False),
    }


SESSION: list[list[tuple[str, str]]] = [
    [
        ("l", "accent"),
        ("@", "subdued"),
        ("vellum", "accent"),
        ("  ", "ink"),
        ("~/Work/tries/vellum-theme", "blue"),
    ],
    [("❯ ", "muted"), ("git status -sb", "ink")],
    [("## ", "subdued"), ("main...origin/main", "green")],
    [(" M ", "red"), ("vellum/colors.toml", "ink")],
    [("?? ", "ochre"), ("screenshots/terminal.png", "ink")],
    [],
    [("❯ ", "muted"), ("rg -c paper vellum/*.toml", "ink")],
    [("vellum/colors.toml:", "blue"), ("4", "num")],
    [],
    [("❯ ", "muted"), ("omarchy theme current", SELECTED)],
    [("Vellum", "accent")],
    [],
    [("❯ ", "muted"), ("eza -l vellum/", "ink")],
    [
        ("drwxr-xr-x  ", "subdued"),
        ("l l  ", "subdued"),
        ("4.0K  ", "num"),
        ("backgrounds", "blue"),
    ],
]


def ansi_slots(foot: dict[str, str]) -> list[tuple[int, str, str]]:
    names = ["ink", "oxide", "moss", "ochre", "indigo", "plum", "teal", "ink"]
    bright_names = ["muted", "oxide", "moss", "ochre", "indigo", "plum", "teal", "secondary"]
    slots = [(i, names[i], "#" + foot[f"regular{i}"]) for i in range(8)]
    slots += [(i + 8, bright_names[i], "#" + foot[f"bright{i}"]) for i in range(8)]
    return slots


# --- cards -----------------------------------------------------------------


def defs(colors: dict[str, str]) -> str:
    return f"""<defs>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">
    <feGaussianBlur stdDeviation="14"/>
  </filter>
  <linearGradient id="seam" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{colors['accent']}"/>
    <stop offset="1" stop-color="{colors['orange']}"/>
  </linearGradient>
</defs>"""


def backdrop(colors: dict[str, str]) -> str:
    """The `0-dawn` wallpaper as a deeper mat, so the windows read as sheets."""
    source = WALL.read_text()
    inner = source[source.index(">", source.index("<svg")) + 1 : source.rindex("</svg>")]
    # the print grain is invisible at card size and only bloats the PNG
    inner = re.sub(r'<rect[^>]*url\(#grain\)[^>]*/>', "", inner)
    scale = W / 2880
    shift = (1920 * scale - H) / 2
    return f"""<rect width="{W}" height="{H}" fill="{colors['background']}"/>
  <g transform="translate(0,{-shift:.1f}) scale({scale})">{inner}</g>
  <rect width="{W}" height="{H}" fill="{colors['darker_background']}" opacity="0.5"/>"""


def window(colors: dict[str, str], title: str, meta: str) -> str:
    x, y, w, h = WIN_X, WIN_Y, WIN_W, WIN_H
    return f"""<rect x="{x + 3}" y="{y + 14}" width="{w}" height="{h}" fill="{colors['foreground']}"
        opacity="0.16" filter="url(#shadow)"/>
  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{colors['background']}"
        stroke="{colors['darker_background']}" stroke-width="1"/>
  <rect x="{x}" y="{y}" width="{w}" height="{HEADER}" fill="{colors['dark_background']}"/>
  <rect x="{x}" y="{y + HEADER}" width="{w}" height="1" fill="{colors['darker_background']}"/>
  <rect x="{x}" y="{y}" width="{w}" height="2" fill="url(#seam)"/>
  <rect x="{x + 20}" y="{y + HEADER - 3}" width="112" height="2" fill="{colors['accent']}"/>
  {text(x + 24, y + 26, title, colors['foreground'], 13.5)}
  {text(x + w - 24, y + 26, meta, colors['muted'], 12, anchor='end')}"""


def syntax_card(colors: dict[str, str]) -> str:
    paper = colors["background"]
    ink = syntax_ink(colors)
    block_h = len(SNIPPET) * CODE_LH
    bottom = WIN_Y + WIN_H - STATUS_H - 12
    top = CONTENT_TOP + max(10, (bottom - CONTENT_TOP - block_h) / 2)

    out = [backdrop(colors), window(colors, "specimens.py", "aether · vellum")]

    # current-line band, drawn under the code it marks
    cur = 10
    y_cur = top + cur * CODE_LH
    out.append(
        f'<rect x="{WIN_X + 1}" y="{y_cur:.1f}" width="{PANEL_X - 30 - WIN_X}" height="{CODE_LH}" '
        f'fill="{colors["darker_background"]}" opacity="0.55"/>'
    )

    for i, spans in enumerate(SNIPPET):
        y = top + i * CODE_LH + 20
        number = colors["accent"] if i == cur else colors["muted"]
        out.append(text(GUTTER, y, str(i + 1), number, 13.5, anchor="end"))
        if spans:
            out.append(spans_line(CODE_X, y, spans, ink))

    # statusline
    sy = WIN_Y + WIN_H - STATUS_H
    out.append(f'<rect x="{WIN_X}" y="{sy}" width="{WIN_W}" height="32" fill="{colors["dark_background"]}"/>')
    out.append(f'<rect x="{WIN_X}" y="{sy}" width="{WIN_W}" height="1" fill="{colors["darker_background"]}"/>')
    out.append(text(WIN_X + PAD, sy + 21, "venv · python3.14", colors["muted"], 12))
    out.append(text(WIN_X + WIN_W - PAD, sy + 21, "utf-8 · 2 spaces", colors["muted"], 12, anchor="end"))

    # ratio rail
    roles = [
        ("Keyword", ink["kw"][0]),
        ("Function", ink["fn"][0]),
        ("Type", ink["type"][0]),
        ("String", ink["str"][0]),
        ("Number", ink["num"][0]),
        ("Constant", ink["const"][0]),
        ("Parameter", ink["param"][0]),
        ("Comment", ink["comment"][0]),
    ]
    row_h = 44
    ph = 56 + len(roles) * row_h + 38
    px, py, pw = PANEL_X, top + (block_h - ph) / 2, PANEL_W
    out.append(
        f'<rect x="{px}" y="{py:.1f}" width="{pw}" height="{ph}" fill="{colors["lighter_background"]}" '
        f'stroke="{colors["darker_background"]}" stroke-width="1"/>'
    )
    out.append(label(px + 20, py + 30, "SYNTAX ON PAPER", colors["muted"]))
    for i, (name, color) in enumerate(roles):
        ry = py + 62 + i * row_h
        out.append(f'<rect x="{px + 20}" y="{ry - 11}" width="12" height="12" fill="{color}"/>')
        out.append(text(px + 42, ry, name, color, 14))
        out.append(text(px + pw - 20, ry, ratio(color, paper), colors["muted"], 12.5, anchor="end"))
    out.append(
        text(px + 20, py + ph - 14, f"measured on {paper}", colors["muted"], 11, italic=True)
    )
    return "".join(out)


def terminal_card(colors: dict[str, str], foot: dict[str, str]) -> str:
    paper = colors["background"]
    ink = terminal_ink(colors)
    slots = ansi_slots(foot)
    x0 = WIN_X + PAD

    session_h = len(SESSION) * CODE_LH
    chip_row, chip_h = 54, 26
    chips_h = 2 * chip_row
    label_gap, note_gap = 40, 30

    stack_h = session_h + label_gap + chips_h + note_gap + 28
    top = CONTENT_TOP + max(12, (CONTENT_H - stack_h) / 2)

    out = [backdrop(colors), window(colors, "foot — vellum", "132 × 32 · truecolor")]

    for i, spans in enumerate(SESSION):
        y = top + i * CODE_LH + 20
        if any(role == SELECTED for _, role in spans):
            width = sum(len(body) for body, _ in spans) * CODE_ADV + 18
            out.append(
                f'<rect x="{x0 - 9}" y="{y - 18:.1f}" width="{width:.1f}" height="{CODE_LH - 2}" '
                f'fill="{colors["selection_background"]}"/>'
            )
        out.append(spans_line(x0, y, spans, ink, limit=CHIP_COLS))

    sep_y = top + session_h + 14
    out.append(
        f'<rect x="{x0}" y="{sep_y:.1f}" width="{WIN_W - 2 * PAD}" height="1" '
        f'fill="{colors["darker_background"]}"/>'
    )
    out.append(label(x0, sep_y + 28, "ANSI SLOTS ON PAPER", colors["muted"]))

    chip_w = (WIN_W - 2 * PAD) / 8
    chip_top = sep_y + label_gap
    for i, (index, name, color) in enumerate(slots):
        cx = x0 + (i % 8) * chip_w
        cy = chip_top + (i // 8) * chip_row
        out.append(f'<rect x="{cx:.1f}" y="{cy}" width="{chip_h}" height="{chip_h}" fill="{color}"/>')
        out.append(text(cx + 32, cy + 12, str(index), colors["muted"], 10.5))
        out.append(text(cx + 48, cy + 12, name, color, 12))
        out.append(text(cx + 48, cy + 26, ratio(color, paper), colors["muted"], 10.5))

    out.append(
        text(
            x0,
            chip_top + chips_h + 6,
            "every slot clears 5:1 · the brights are darker, never washed out",
            colors["muted"],
            12,
            italic=True,
        )
    )
    return "".join(out)


def menu_card(colors: dict[str, str], shell: dict[str, dict[str, object]]) -> str:
    bar = shell["bar"]
    menu = shell["menu"]
    paper, ink = colors["background"], colors["foreground"]
    card = str(menu["background"])
    border = str(menu["border"])
    sel_fill = mix(str(menu["selected-background"]), card, float(menu["selected-background-alpha"]))
    sel_text = str(menu["selected-text"])
    bar_bg = str(bar["background"])

    out = [backdrop(colors), window(colors, "vellum shell", "bar · menu · notification")]

    # the bar: one sheet deeper than the page
    bar_h = 36
    out.append(f'<rect x="{WIN_X}" y="{CONTENT_TOP}" width="{WIN_W}" height="{bar_h}" fill="{bar_bg}"/>')
    out.append(
        f'<rect x="{WIN_X}" y="{CONTENT_TOP + bar_h}" width="{WIN_W}" height="1" fill="{colors["darker_background"]}"/>'
    )
    base = CONTENT_TOP + 24
    for i, tag in enumerate(["1", "2", "3", "4", "5"]):
        active = tag == "2"
        out.append(
            text(
                WIN_X + PAD + i * 22,
                base,
                tag,
                str(bar["active"]) if active else colors["muted"],
                13,
                weight=700 if active else 400,
            )
        )
    out.append(text(WIN_X + PAD + 128, base, "foot", ink, 12.5))
    out.append(
        text(WIN_X + WIN_W - PAD, base, "cpu 12% · mem 38% · 14:07", colors["muted"], 12.5, anchor="end")
    )

    block_h = 272
    top = CONTENT_TOP + bar_h + (WIN_H - HEADER - bar_h - block_h) / 2

    # the menu: card sheet, hairline, mist selection
    items = ["Apps", "Learn", "Theme", "Background", "Screenshot", "System"]
    selected = 2
    mx, mw, row_h, pad_y = WIN_X + PAD, 320, 34, 12
    mh = pad_y * 2 + len(items) * row_h
    out.append(
        f'<rect x="{mx + 3}" y="{top + 12}" width="{mw}" height="{mh}" fill="{ink}" opacity="0.15" filter="url(#shadow)"/>'
    )
    out.append(
        f'<rect x="{mx}" y="{top:.1f}" width="{mw}" height="{mh}" fill="{card}" stroke="{border}" stroke-width="1"/>'
    )
    for i, item in enumerate(items):
        ry = top + pad_y + i * row_h + 23
        if i == selected:
            out.append(
                f'<rect x="{mx + 1}" y="{top + pad_y + i * row_h:.1f}" width="{mw - 2}" height="{row_h}" '
                f'fill="{sel_fill}"/>'
            )
            out.append(text(mx + 20, ry, item, sel_text, 14.5, weight=700))
        else:
            out.append(text(mx + 20, ry, item, ink, 14.5))

    # a notification: one sheet lighter, countdown in accent
    nx, nw = mx + mw + 40, 320
    nh = 120
    out.append(
        f'<rect x="{nx + 3}" y="{top + 12}" width="{nw}" height="{nh}" fill="{ink}" opacity="0.15" filter="url(#shadow)"/>'
    )
    out.append(
        f'<rect x="{nx}" y="{top:.1f}" width="{nw}" height="{nh}" fill="{card}" stroke="{border}" stroke-width="1"/>'
    )
    out.append(text(nx + 20, top + 34, "Screenshots saved", ink, 14.5))
    out.append(text(nx + 20, top + 58, "~/Pictures/Screenshots", colors["muted"], 12.5))
    out.append(
        f'<rect x="{nx + 20}" y="{top + nh - 20}" width="{nw - 40}" height="3" fill="{colors["darker_background"]}"/>'
    )
    out.append(f'<rect x="{nx + 20}" y="{top + nh - 20}" width="{(nw - 40) * 0.62:.0f}" height="3" fill="{colors["accent"]}"/>')

    # measured pairs
    rows = [
        ("Bar ink", ink, bar_bg, contrast(ink, bar_bg)),
        ("Menu ink", ink, card, contrast(ink, card)),
        ("Selected", sel_text, sel_fill, contrast(sel_text, sel_fill)),
        ("Hairline", border, card, contrast(border, card)),
    ]
    px, pw = nx + nw + 40, WIN_X + WIN_W - PAD - (nx + nw + 40)
    ph = 56 + len(rows) * 44 + 46
    out.append(
        f'<rect x="{px}" y="{top:.1f}" width="{pw}" height="{ph}" fill="{colors["lighter_background"]}" '
        f'stroke="{border}" stroke-width="1"/>'
    )
    out.append(label(px + 18, top + 30, "SURFACES ON PAPER", colors["muted"]))
    for i, (name, front, back, value) in enumerate(rows):
        ry = top + 62 + i * 44
        out.append(f'<rect x="{px + 18}" y="{ry - 11}" width="12" height="12" fill="{back}" stroke="{border}"/>')
        out.append(text(px + 40, ry, name, front, 13.5))
        out.append(text(px + pw - 18, ry, f"{value:.1f}:1", colors["muted"], 12.5, anchor="end"))
    out.append(
        text(
            px + 18,
            top + ph - 16,
            "hairline delimits, it never carries text",
            colors["muted"],
            10.5,
            italic=True,
        )
    )
    return "".join(out)


def svg_doc(body: str, colors: dict[str, str], title: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <title>{esc(title)}</title>
  {defs(colors)}
  {body}
</svg>
"""


def render(name: str, body: str, colors: dict[str, str], title: str) -> Path:
    OUT.mkdir(exist_ok=True)
    target = OUT / f"{name}.png"
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / f"{name}.svg"
        source.write_text(svg_doc(body, colors, title))
        subprocess.run(
            ["rsvg-convert", "--zoom", "2", "-o", str(target), str(source)],
            check=True,
        )
    subprocess.run(
        ["magick", str(target), "-strip", "-define", "png:compression-level=9", str(target)],
        check=True,
    )
    return target


def main() -> None:
    colors = load_colors()
    foot = load_foot()
    cards = {
        "syntax": (syntax_card(colors), "Vellum: syntax highlighting on paper"),
        "terminal": (terminal_card(colors, foot), "Vellum: terminal ANSI slots on paper"),
        "surfaces": (menu_card(colors, load_shell()), "Vellum: bar, menu and notification surfaces"),
    }
    for name in sys.argv[1:] or list(cards):
        body, title = cards[name]
        path = render(name, body, colors, title)
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KiB")


if __name__ == "__main__":
    main()

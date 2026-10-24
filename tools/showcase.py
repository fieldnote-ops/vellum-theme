#!/usr/bin/env python3
"""Print a Vellum palette/showcase card for screenshots and the theme picker."""

from __future__ import annotations

PAPER = (247, 243, 234)
INK = (66, 63, 54)
VERDIGRIS = (44, 106, 89)
CLAY = (156, 79, 23)
MUTED = (97, 92, 81)
COMMENT = (107, 101, 88)

COLORS = [
    ("oxide", (156, 58, 50), "#9c3a32"),
    ("moss", (66, 104, 43), "#42682b"),
    ("ochre", (120, 89, 11), "#78590b"),
    ("indigo", (43, 87, 144), "#2b5790"),
    ("plum", (125, 60, 101), "#7d3c65"),
    ("teal", (24, 105, 101), "#186965"),
    ("clay", (156, 79, 23), "#9c4f17"),
    ("brown", (112, 66, 37), "#704225"),
]

FONT = {
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "E": ["11111", "10000", "11110", "10000", "11111", "10000", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "U": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"],
}


def fg(rgb: tuple[int, int, int]) -> str:
    return f"\x1b[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"


def bg(rgb: tuple[int, int, int]) -> str:
    return f"\x1b[48;2;{rgb[0]};{rgb[1]};{rgb[2]}m"


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


def banner() -> list[str]:
    word = "VELLUM"
    rows: list[list[tuple[int, int, int] | None]] = []
    width = len(word) * 6 - 1
    for y in range(7):
        row: list[tuple[int, int, int] | None] = []
        for x in range(width):
            letter = x // 6
            col = x % 6
            on = col < 5 and FONT[word[letter]][y][col] == "1"
            row.append(mix(VERDIGRIS, CLAY, x / (width - 1)) if on else None)
        rows.append(row)

    out: list[str] = []
    for y in range(0, 7, 2):
        line = ""
        for x in range(width):
            top = rows[y][x]
            bottom = rows[y + 1][x] if y + 1 < 7 else None
            if top and bottom:
                line += fg(top) + bg(bottom) + "▀"
            elif top:
                line += fg(top) + "▀"
            elif bottom:
                line += fg(bottom) + "▄"
            else:
                line += " "
        out.append(line + "\x1b[0m")
    return out


def swatch(name: str, rgb: tuple[int, int, int], hexcode: str) -> str:
    return f"{bg(rgb)}   \x1b[0m {fg(rgb)}{name:<7}{hexcode}\x1b[0m"


def main() -> None:
    print("\n" + "\n".join(banner()))
    print(f"  {fg(INK)}sun-warmed paper · iron-gall ink · verdigris edge\x1b[0m")
    print()

    print(f"  {fg(MUTED)}PALETTE — every ANSI color ≥ 5:1 on paper\x1b[0m")
    for row in (COLORS[:4], COLORS[4:]):
        print("  " + "  ".join(swatch(*item) for item in row))
    print()

    print(f"  {fg(MUTED)}TYPE\x1b[0m")
    print(f"  {fg(INK)}The quick brown fox jumps over the lazy dog.\x1b[0m")
    print(f"  {fg(INK)}Sphinx of black quartz, judge my vow.  0123456789\x1b[0m")
    print(f"  {fg(MUTED)}muted ink for metadata and timestamps\x1b[0m")
    print(f"  {fg(COMMENT)}comment ink stays readable at 5.2:1, never ghost-gray\x1b[0m")
    print()

    print(f"  {fg(MUTED)}CODE\x1b[0m")
    code = [
        ([(INK, "pub fn "), (VERDIGRIS, "palette"), (INK, "() -> "), (CLAY, "Paper"), (INK, " {")]),
        ([(INK, "    let "), (INK, "ink"), (INK, " = "), (MUTED, "\"#423f36\""), (INK, "  "), (MUTED, "// 9.5:1"), (INK, "")]),
        ([(INK, "    "), (VERDIGRIS, "Paper::new"), (INK, "("), (MUTED, "\"vellum\""), (INK, ", "), (CLAY, "0.055"), (INK, ")")]),
        ([(INK, "}")]),
    ]
    for line in code:
        print("  " + "".join(fg(color) + text + "\x1b[0m" for color, text in line))
    print()
    print("  \x1b[30mANSI black is readable ink, not paper-on-paper.\x1b[0m")
    print()
    print(f"  {fg(MUTED)}PAPER #f7f3ea  ·  INK #423f36  ·  ACCENT #2c6a59  ·  YARU-SAGE\x1b[0m")
    print()


if __name__ == "__main__":
    main()

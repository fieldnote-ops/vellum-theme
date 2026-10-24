#!/usr/bin/env python3
"""Generate Vellum's wallpaper variants.

The source of truth is geometry plus the palette below; rsvg-convert renders
each SVG to PNG and ImageMagick compresses it to a print-quality JPEG.
"""

from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from pathlib import Path

W, H = 2880, 1920
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "vellum" / "backgrounds"
SRC = ROOT / "tools" / "backgrounds-src"

PAPER = "#f7f3ea"
PAPER_HI = "#fcf9f2"
PAPER_LO = "#f0e9db"
INK = "#26251f"
VERDIGRIS = "#2c6a59"
CLAY = "#a85719"
SAGE = "#6a6559"

GRAIN = """
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4"
                  seed="11" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
"""


def svg_doc(body: str, extra_defs: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{PAPER_HI}"/>
      <stop offset="0.55" stop-color="{PAPER}"/>
      <stop offset="1" stop-color="{PAPER_LO}"/>
    </linearGradient>
    {extra_defs}
    {GRAIN}
  </defs>
  <rect width="{W}" height="{H}" fill="url(#paper)"/>
  {body}
  <rect width="{W}" height="{H}" filter="url(#grain)" opacity="0.055"
        style="mix-blend-mode:multiply"/>
</svg>
"""


def arc(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M {x0:.1f} {y0:.1f} A {r:.1f} {r:.1f} 0 {large} 1 {x1:.1f} {y1:.1f}"


def dawn() -> str:
    defs = f"""
    <radialGradient id="sunGlow" cx="0.78" cy="0.25" r="0.62">
      <stop offset="0" stop-color="#fff6da" stop-opacity="0.95"/>
      <stop offset="0.55" stop-color="#fff6da" stop-opacity="0.38"/>
      <stop offset="1" stop-color="#fff6da" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="sunDisc" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#f1d59a" stop-opacity="0.62"/>
      <stop offset="0.72" stop-color="#f5e3bd" stop-opacity="0.20"/>
      <stop offset="1" stop-color="#f5e3bd" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="haze" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e8dfce" stop-opacity="0"/>
      <stop offset="1" stop-color="#e8dfce" stop-opacity="0.55"/>
    </linearGradient>
    """
    cx, cy = 2260, 520
    parts = [
        '<rect width="2880" height="1920" fill="url(#sunGlow)"/>',
        f'<circle cx="{cx}" cy="{cy}" r="360" fill="url(#sunDisc)"/>',
    ]
    rings = [
        (390, VERDIGRIS, 2.4, 0.10, 188, 336),
        (520, CLAY, 1.8, 0.065, 160, 308),
        (680, VERDIGRIS, 1.6, 0.05, 198, 350),
        (860, SAGE, 1.4, 0.035, 172, 330),
        (1070, CLAY, 1.2, 0.022, 150, 300),
    ]
    for r, color, width, opacity, a0, a1 in rings:
        parts.append(
            f'<path d="{arc(cx, cy, r, a0, a1)}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" opacity="{opacity}"/>'
        )

    contours = [
        ("M -180 1560 C 520 1430 880 1700 1420 1540 S 2380 1430 3060 1580", VERDIGRIS, 3.2, 0.070),
        ("M -180 1625 C 520 1495 880 1765 1420 1605 S 2380 1495 3060 1645", SAGE, 2.0, 0.045),
        ("M -180 1700 C 520 1570 880 1840 1420 1680 S 2380 1570 3060 1720", CLAY, 1.6, 0.038),
    ]
    for d, color, width, opacity in contours:
        parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" opacity="{opacity}"/>'
        )
    parts.append('<rect y="1460" width="2880" height="460" fill="url(#haze)"/>')
    return svg_doc("".join(parts), defs)


def ripple() -> str:
    defs = f"""
    <radialGradient id="cool" cx="0.18" cy="0.12" r="0.7">
      <stop offset="0" stop-color="{PAPER_HI}" stop-opacity="0.9"/>
      <stop offset="1" stop-color="{PAPER_HI}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="warm" cx="0.9" cy="0.92" r="0.55">
      <stop offset="0" stop-color="#f0dfc2" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#f0dfc2" stop-opacity="0"/>
    </radialGradient>
    """
    cx, cy = 3160, 2140
    parts = [
        '<rect width="2880" height="1920" fill="url(#cool)"/>',
        '<rect width="2880" height="1920" fill="url(#warm)"/>',
    ]
    # Concentric sweeps; alternation keeps the rings from reading as a target.
    for i, r in enumerate(range(620, 2900, 158)):
        color = VERDIGRIS if i % 3 else CLAY
        width = 3.4 if i % 7 == 0 else 1.7
        opacity = 0.085 - min(i * 0.0035, 0.055)
        a0 = 174 + (i % 5) * 7
        a1 = 316 - (i % 4) * 9
        parts.append(
            f'<path d="{arc(cx, cy, r, a0, a1)}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" opacity="{opacity:.3f}"/>'
        )
    # One long horizon stroke anchors the composition.
    parts.append(
        f'<path d="M -120 1240 C 700 1170 1200 1310 1900 1210 S 2700 1160 3000 1190" '
        f'fill="none" stroke="{VERDIGRIS}" stroke-width="1.8" opacity="0.07"/>'
    )
    return svg_doc("".join(parts), defs)


def strata() -> str:
    defs = f"""
    <radialGradient id="sun" cx="0.82" cy="0.18" r="0.5">
      <stop offset="0" stop-color="#f4dfb4" stop-opacity="0.62"/>
      <stop offset="1" stop-color="#f4dfb4" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="bandA" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e8dfce" stop-opacity="0.78"/>
      <stop offset="1" stop-color="#e8dfce" stop-opacity="0.22"/>
    </linearGradient>
    <linearGradient id="bandB" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#dfe6da" stop-opacity="0.72"/>
      <stop offset="1" stop-color="#dfe6da" stop-opacity="0.18"/>
    </linearGradient>
    <linearGradient id="bandC" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ecdcc8" stop-opacity="0.62"/>
      <stop offset="1" stop-color="#ecdcc8" stop-opacity="0.12"/>
    </linearGradient>
    """
    parts = ['<rect width="2880" height="1920" fill="url(#sun)"/>']

    bands = [
        (1080, 150, "url(#bandA)", VERDIGRIS, 2.2, 0.085),
        (1230, 140, "url(#bandB)", SAGE, 1.5, 0.050),
        (1370, 130, "url(#bandC)", CLAY, 1.8, 0.060),
        (1510, 125, "url(#bandA)", VERDIGRIS, 1.4, 0.045),
        (1650, 115, "url(#bandB)", SAGE, 1.2, 0.035),
    ]
    for y, amp, fill, stroke, width, opacity in bands:
        top = (
            f"M -120 {y} C 420 {y - amp} 760 {y + amp} 1260 {y - amp * 0.35} "
            f"S 2260 {y + amp * 0.7} 3000 {y - amp * 0.2}"
        )
        parts.append(f'<path d="{top} L 3000 2020 L -120 2020 Z" fill="{fill}"/>')
        parts.append(
            f'<path d="{top}" fill="none" stroke="{stroke}" stroke-width="{width}" '
            f'stroke-linecap="round" opacity="{opacity}"/>'
        )
    return svg_doc("".join(parts), defs)


def fold() -> str:
    """A folded-sheet composition: broad crease shadows, thin highlights, two
    ink hairlines. It reads as the same paper stock as the other three while
    changing the visual language from rings/contours to plane and crease."""
    defs = """
    <filter id="foldBlur" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="18"/>
    </filter>
    <filter id="foldTight" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="5"/>
    </filter>
    """
    parts: list[str] = []

    # d, shadow width, shadow opacity, highlight dx, highlight dy
    creases = [
        ("M 260 -140 C 660 420 820 980 540 2060", 96, 0.060, 9, -6),
        ("M 3120 -140 C 2460 520 2260 1180 2700 2060", 118, 0.052, -11, -6),
        ("M -140 1510 C 760 1420 1880 1640 3020 1480", 72, 0.045, 0, -8),
    ]
    for d, width, opacity, hx, hy in creases:
        parts.append(
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{width}" '
            f'stroke-linecap="round" opacity="{opacity}" filter="url(#foldBlur)"/>'
        )
        parts.append(
            f'<path d="{d}" fill="none" stroke="#fffdf6" stroke-width="{width * 0.26:.1f}" '
            f'stroke-linecap="round" opacity="0.28" filter="url(#foldTight)" '
            f'transform="translate({hx} {hy})"/>'
        )
        # A fine line gives the diffuse shadow an edge to read against.
        parts.append(
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="1.1" '
            f'stroke-linecap="round" opacity="0.085"/>'
        )

    # The crease itself catches one verdigris and one clay hairline; the
    # highlights stay neutral so the folds do not read as coloured ribbons.
    parts.append(
        f'<path d="M 260 -140 C 660 420 820 980 540 2060" fill="none" '
        f'stroke="{VERDIGRIS}" stroke-width="1.4" stroke-linecap="round" '
        f'opacity="0.060" transform="translate(3 -1)"/>'
    )
    parts.append(
        f'<path d="M -140 1510 C 760 1420 1880 1640 3020 1480" fill="none" '
        f'stroke="{CLAY}" stroke-width="1.2" stroke-linecap="round" '
        f'opacity="0.045" transform="translate(0 -2)"/>'
    )
    return svg_doc("".join(parts), defs)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    variants = {
        "0-dawn": dawn,
        "1-ripple": ripple,
        "2-strata": strata,
        "3-fold": fold,
    }
    names = sys.argv[1:] or list(variants)
    unknown = [name for name in names if name not in variants]
    if unknown:
        raise SystemExit("unknown wallpaper: " + ", ".join(unknown))
    for name in names:
        builder = variants[name]
        svg = SRC / f"{name}.svg"
        jpg = OUT / f"{name}.jpg"
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / f"{name}.png"
            svg.write_text(builder())
            subprocess.run(
                ["rsvg-convert", "-w", str(W), "-h", str(H), "-o", str(png), str(svg)],
                check=True,
            )
            subprocess.run(
                ["magick", str(png), "-sampling-factor", "4:2:0", "-quality", "92", str(jpg)],
                check=True,
            )
        print(f"{jpg.name}: {jpg.stat().st_size // 1024} KiB")


if __name__ == "__main__":
    main()

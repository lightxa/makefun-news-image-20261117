#!/usr/bin/env python3
"""Draw a one-page front-page montage summing up Tuesday 17 November 2026
world news and write it to $MAKEFUN_OUTPUT_DIR/entry.png.

Stdlib only, no network, no randomness, no time dependence: the same input
always produces the same bytes.
"""

import os
import struct
import zlib

# ---------------------------------------------------------------------------
# 5x7 bitmap font, drawn by hand for this entry. Each glyph is 7 rows of
# 5 characters; "#" is an inked pixel. Uppercase only; text is uppercased
# before drawing. Unknown characters render as a blank.
# ---------------------------------------------------------------------------

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
}


def text_width(text, scale):
    """Pixel width of text at the given scale (6 px per glyph cell)."""
    return len(text) * 6 * scale


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines that fit max_width px."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Canvas: a plain RGB bytearray with simple drawing primitives.
# ---------------------------------------------------------------------------

class Canvas:
    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.pixels = bytearray(background) * (width * height)

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i:i + 3] = color

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.width + x0) * 3
            self.pixels[i:i + len(row)] = row

    def rect(self, x, y, w, h, color, thickness=1):
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def hline(self, x, y, length, color, thickness=1):
        self.fill_rect(x, y, length, thickness, color)

    def vline(self, x, y, length, color, thickness=1):
        self.fill_rect(x, y, thickness, length, color)

    def line(self, x0, y0, x1, y1, color, thickness=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.fill_rect(x0, y0, thickness, thickness, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def filled_circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            span = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - span, cy + dy, span * 2 + 1, 1, color)

    def circle(self, cx, cy, r, color, thickness=1):
        for dy in range(-r, r + 1):
            span = int((r * r - dy * dy) ** 0.5)
            for t in range(thickness):
                self.set_pixel(cx - span + t, cy + dy, color)
                self.set_pixel(cx + span - t, cy + dy, color)

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        # Filled triangle by scanline interpolation.
        pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        if ay == cy:
            return
        def edge_x(y, p, q):
            if p[1] == q[1]:
                return p[0]
            return p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1])
        for y in range(ay, cy + 1):
            if y < by:
                xa = edge_x(y, (ax, ay), (bx, by))
            else:
                xa = edge_x(y, (bx, by), (cx, cy))
            xb = edge_x(y, (ax, ay), (cx, cy))
            lo, hi = sorted([int(xa), int(xb)])
            self.fill_rect(lo, y, hi - lo + 1, 1, color)

    def draw_text(self, x, y, text, color, scale=1, bold=False):
        """Draw text left-aligned at (x, y). Returns the width in pixels."""
        text = text.upper()
        cx = x
        for ch in text:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
                        if bold:
                            self.fill_rect(cx + col * scale + 1,
                                           y + row * scale, scale, scale,
                                           color)
            cx += 6 * scale
        return cx - x

    def draw_text_centered(self, x, y, w, text, color, scale=1, bold=False):
        tw = text_width(text.upper(), scale) + (scale if bold else 0)
        self.draw_text(x + (w - tw) // 2, y, text, color, scale, bold)


# ---------------------------------------------------------------------------
# Minimal PNG encoder: 8-bit RGB, filter 0, zlib level 9. Deterministic.
# ---------------------------------------------------------------------------

def encode_png(canvas):
    width = canvas.width
    height = canvas.height
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        start = y * stride
        raw += canvas.pixels[start:start + stride]
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    return png

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

INK = bytes([24, 28, 38])
PAPER = bytes([250, 247, 238])
NAVY = bytes([18, 38, 74])
NAVY_LIGHT = bytes([38, 62, 104])
WHITE = bytes([255, 255, 255])
GREY = bytes([110, 112, 118])
LIGHT_GREY = bytes([226, 222, 212])
SKY = bytes([168, 205, 228])
SEA = bytes([44, 96, 140])
DARK_SEA = bytes([28, 70, 108])
FIRE = bytes([232, 88, 34])
SMOKE = bytes([120, 122, 126])
GOLD = bytes([214, 164, 32])
RED = bytes([196, 38, 38])
GREEN = bytes([34, 120, 60])
BROWN = bytes([122, 82, 42])
SAND = bytes([232, 214, 168])


def burst(c, cx, cy, r, color):
    """Starburst: 8 spikes from a centre, like an explosion flash."""
    c.filled_circle(cx, cy, r // 2, color)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                   (1, 1), (1, -1), (-1, 1), (-1, -1)):
        c.line(cx, cy, cx + dx * r, cy + dy * r, color, 3)


def draw_waves(c, x, y, w, color):
    for i in range(0, w, 26):
        c.line(x + i, y, x + i + 12, y - 4, color, 2)
        c.line(x + i + 12, y - 4, x + i + 24, y, color, 2)


# ---------------------------------------------------------------------------
# Story scenes. Each draws inside the rectangle (x, y, w, h).
# ---------------------------------------------------------------------------

def scene_bridge(c, x, y, w, h):
    """Kerch Bridge over the strait, hit by an explosion."""
    c.fill_rect(x, y, w, h, SKY)
    c.fill_rect(x, y + h - 26, w, 26, SEA)
    draw_waves(c, x + 4, y + h - 12, w - 8, DARK_SEA)
    # Two towers and the deck.
    for tx in (x + 90, x + w - 150):
        c.fill_rect(tx, y + 22, 10, h - 48, INK)
        c.fill_rect(tx - 4, y + 16, 18, 8, INK)
    c.fill_rect(x, y + 62, w, 8, INK)
    for px in range(x + 6, x + w - 6, 22):
        c.vline(px, y + 70, 22, INK, 2)
    # Cables from tower tops to the deck.
    c.line(x + 95, y + 22, x + 30, y + 62, INK, 2)
    c.line(x + 95, y + 22, x + 170, y + 62, INK, 2)
    c.line(x + w - 145, y + 22, x + w - 220, y + 62, INK, 2)
    c.line(x + w - 145, y + 22, x + w - 70, y + 62, INK, 2)
    # Explosion above the deck, mid-span, with smoke.
    burst(c, x + w // 2, y + 34, 30, FIRE)
    c.filled_circle(x + w // 2 - 34, y + 18, 12, SMOKE)
    c.filled_circle(x + w // 2 + 36, y + 14, 10, SMOKE)
    c.filled_circle(x + w // 2, y + 6, 9, SMOKE)


def scene_kyiv(c, x, y, w, h):
    """Kyiv skyline and a Dnipro bridge under smoke."""
    c.fill_rect(x, y, w, h, SKY)
    c.filled_circle(x + w - 60, y + 22, 16, GOLD)
    # Skyline silhouettes.
    for bx, bw, bh in ((x + 8, 44, 52), (x + 58, 30, 78), (x + 94, 52, 44),
                       (x + 152, 26, 88), (x + 184, 48, 58),
                       (x + 238, 34, 72), (x + 278, 40, 48),
                       (x + 324, 28, 84), (x + 358, 46, 60),
                       (x + 410, 30, 80)):
        c.fill_rect(bx, y + h - 30 - bh, bw, bh, NAVY_LIGHT)
    # Church dome on one tower.
    c.filled_circle(x + 165, y + h - 30 - 88, 10, GOLD)
    # River and bridge.
    c.fill_rect(x, y + h - 30, w, 30, SEA)
    c.fill_rect(x, y + h - 52, w, 6, INK)
    for px in range(x + 10, x + w - 10, 30):
        c.vline(px, y + h - 46, 16, INK, 2)
    # Smoke columns rising from the bridge.
    c.filled_circle(x + 120, y + h - 66, 12, SMOKE)
    c.filled_circle(x + 132, y + h - 86, 10, SMOKE)
    c.filled_circle(x + 330, y + h - 62, 11, SMOKE)
    c.filled_circle(x + 344, y + h - 80, 9, SMOKE)
    burst(c, x + 300, y + h - 56, 16, FIRE)


def scene_gulf(c, x, y, w, h):
    """A tanker in the Gulf, a spiked mine, and an intercepted drone."""
    c.fill_rect(x, y, w, h, SKY)
    c.fill_rect(x, y + h - 44, w, 44, SEA)
    draw_waves(c, x + 4, y + h - 20, w - 8, DARK_SEA)
    # Tanker hull, deck and funnel.
    c.fill_rect(x + 60, y + h - 66, 300, 24, RED)
    c.triangle(x + 60, y + h - 66, x + 360, y + h - 66,
               x + 360, y + h - 42, RED)
    c.fill_rect(x + 96, y + h - 92, 70, 26, WHITE)
    c.fill_rect(x + 280, y + h - 96, 22, 30, INK)
    c.fill_rect(x + 120, y + h - 104, 8, 12, INK)
    # Spiked mine in the water ahead of the tanker.
    mx, my = x + w - 60, y + h - 26
    c.filled_circle(mx, my, 12, INK)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                   (1, 1), (1, -1), (-1, 1), (-1, -1)):
        c.line(mx, my, mx + dx * 18, my + dy * 18, INK, 2)
    burst(c, mx - 26, my - 16, 18, FIRE)
    # Drone in the sky, crossed out: intercepted.
    dx, dy = x + 70, y + 22
    c.line(dx - 18, dy, dx + 18, dy, INK, 3)
    c.line(dx, dy - 6, dx, dy + 6, INK, 3)
    c.filled_circle(dx - 18, dy, 4, INK)
    c.filled_circle(dx + 18, dy, 4, INK)
    c.line(dx - 26, dy - 16, dx + 26, dy + 16, RED, 4)
    c.line(dx - 26, dy + 16, dx + 26, dy - 16, RED, 4)


def scene_summit(c, x, y, w, h):
    """Three flags over a summit table: China, United States, Russia."""
    c.fill_rect(x, y, w, h, SAND)
    c.fill_rect(x, y + h - 26, w, 26, BROWN)
    # Table.
    c.fill_rect(x + 40, y + h - 62, w - 80, 10, BROWN)
    for lx in (x + 60, x + w - 70):
        c.fill_rect(lx, y + h - 52, 8, 26, BROWN)
    # Three flags on poles behind the table.
    flags = [
        (x + 90, RED, "CN"),
        (x + w // 2 - 30, NAVY, "US"),
        (x + w - 150, WHITE, "RU"),
    ]
    for fx, fcolor, code in flags:
        c.fill_rect(fx, y + 12, 5, 62, INK)
        c.fill_rect(fx + 5, y + 12, 56, 34, fcolor)
        if code == "US":
            for sy in range(6):
                c.fill_rect(fx + 5, y + 12 + sy * 6, 56, 3, RED)
            c.fill_rect(fx + 5, y + 12, 24, 18, NAVY)
        if code == "RU":
            c.fill_rect(fx + 5, y + 12, 56, 11, WHITE)
            c.fill_rect(fx + 5, y + 23, 56, 12, NAVY_LIGHT)
            c.fill_rect(fx + 5, y + 35, 56, 11, RED)
        if code == "CN":
            for sx, sy in ((10, 4), (22, 8), (26, 16), (16, 20)):
                c.filled_circle(fx + 5 + sx, y + 12 + sy, 3, GOLD)
        # Seated figure: head and shoulders at the table.
        c.filled_circle(fx + 32, y + h - 78, 9, INK)
        c.fill_rect(fx + 18, y + h - 68, 28, 10, INK)
    # Names on the table band, under each flag.
    for fx, _color, code in flags:
        c.draw_text_centered(fx - 8, y + h - 61, 80, code, WHITE, 1)


def scene_rwanda(c, x, y, w, h):
    """A plane flying toward a hub, with the five states' flags."""
    c.fill_rect(x, y, w, h, SKY)
    c.filled_circle(x + w - 56, y + 24, 15, GOLD)
    # Runway and hub building.
    c.fill_rect(x, y + h - 24, w, 24, GREEN)
    c.fill_rect(x + 30, y + h - 66, 90, 42, BROWN)
    c.fill_rect(x + 56, y + h - 66, 38, 10, RED)
    for wx in (x + 42, x + 66, x + 90):
        c.fill_rect(wx, y + h - 52, 12, 12, GOLD)
    # Airplane in flight, nose to the right, top centre-left.
    px, py = x + 140, y + 10
    c.triangle(px, py, px + 130, py + 10, px, py + 20, NAVY)
    c.triangle(px + 40, py - 14, px + 70, py - 14, px + 66, py + 6, NAVY)
    c.triangle(px + 96, py + 12, px + 116, py + 12, px + 110, py + 26, NAVY)
    # Dashed flight path descending from the plane to the hub.
    for i in range(12):
        cx = px + 140 - i * 16
        cy = py + 14 + i * 3
        c.fill_rect(cx, cy, 8, 3, INK)
    # Five flag chips: Germany, Denmark, Austria, Greece, Netherlands.
    chips = [
        ("DE", (INK, RED, GOLD)),
        ("DK", (RED, WHITE, RED)),
        ("AT", (RED, WHITE, RED)),
        ("GR", (NAVY_LIGHT, WHITE, NAVY_LIGHT)),
        ("NL", (RED, WHITE, NAVY_LIGHT)),
    ]
    for i, (code, stripes) in enumerate(chips):
        fx = x + 150 + i * 62
        fy = y + h - 52
        for s, col in enumerate(stripes):
            c.fill_rect(fx, fy + s * 7, 52, 7, col)
        c.rect(fx, fy, 52, 21, INK, 1)
        c.draw_text_centered(fx, fy + 26, 52, code, INK, 1)


def scene_jets(c, x, y, w, h):
    """Two jets scramble into a cloudy sky, radar arcs below."""
    c.fill_rect(x, y, w, h, SKY)
    # Clouds.
    for cx, cy, r in ((x + 60, y + 20, 14), (x + 84, y + 16, 16),
                      (x + 108, y + 22, 12), (x + w - 130, y + 76, 13),
                      (x + w - 106, y + 72, 15), (x + w - 84, y + 78, 11)):
        c.filled_circle(cx, cy, r, WHITE)
    # Radar arcs bottom left, kept inside the scene.
    for r in (12, 22, 30):
        c.circle(x + 34, y + h - 34, r, NAVY, 2)
    c.filled_circle(x + 34, y + h - 34, 5, RED)
    # Jet 1 climbing right, jet 2 climbing left, with contrails.
    def jet(jx, jy, flip):
        s = -1 if flip else 1
        c.triangle(jx, jy, jx + s * 96, jy + 12, jx, jy + 24, INK)
        c.triangle(jx + s * 34, jy - 12, jx + s * 58, jy - 12,
                   jx + s * 56, jy + 8, INK)
        c.triangle(jx + s * 70, jy + 14, jx + s * 88, jy + 14,
                   jx + s * 82, jy + 26, INK)
        c.line(jx - 6, jy + 12, jx - s * 90, jy + 12, WHITE, 4)
    jet(x + 190, y + 34, False)
    jet(x + w - 210, y + 66, True)
    # Small red star marking the intruder's path.
    c.filled_circle(x + w - 60, y + 30, 8, RED)
    c.draw_text(x + w - 96, y + 44, "INTRUDER", RED, 1)

# ---------------------------------------------------------------------------
# Front-page layout
# ---------------------------------------------------------------------------

STORIES = [
    {
        "kicker": "UKRAINE  -  BLACK SEA",
        "accent": NAVY,
        "scene": scene_bridge,
        "headline": "KERCH BRIDGE HIT AGAIN",
        "body": ("Ukraine strikes the bridge a second day running. "
                 "Zelenskyy hails an \"unprecedented operation\"."),
    },
    {
        "kicker": "UKRAINE  -  KYIV",
        "accent": FIRE,
        "scene": scene_kyiv,
        "headline": "MISSILES HIT KYIV BRIDGES",
        "body": ("Russian strikes on Dnipro crossings disrupt heating, "
                 "water and power in the capital."),
    },
    {
        "kicker": "THE GULF",
        "accent": SEA,
        "scene": scene_gulf,
        "headline": "TANKERS HIT MINES OFF HORMUZ",
        "body": ("Iran drones fired at a US radar base in Bahrain are "
                 "intercepted. No casualties reported."),
    },
    {
        "kicker": "CHINA  -  DIPLOMACY",
        "accent": RED,
        "scene": scene_summit,
        "headline": "XI, TRUMP, PUTIN TO MEET",
        "body": ("China confirms a three-way summit on Thursday 19 Nov "
                 "in Shenzhen, on APEC sidelines."),
    },
    {
        "kicker": "EUROPE  -  MIGRATION",
        "accent": GREEN,
        "scene": scene_rwanda,
        "headline": "FIVE STATES PLAN RWANDA HUB",
        "body": ("Germany, Denmark, Austria, Greece and the Netherlands "
                 "plan a joint migrant return hub."),
    },
    {
        "kicker": "JAPAN  -  AIRSPACE",
        "accent": NAVY_LIGHT,
        "scene": scene_jets,
        "headline": "JETS SCRAMBLED OVER INCURSION",
        "body": ("Japan scrambles jets after suspected Russian aircraft "
                 "are reported violating its airspace."),
    },
]

FOOTER = ("ALSO: PENTAGON FAILS AUDIT, 9TH YEAR  -  "
          "UN GENEVA TALKS ON AUTONOMOUS WEAPONS BAN")


def draw_panel(c, x, y, w, h, story):
    c.fill_rect(x, y, w, h, WHITE)
    c.rect(x, y, w, h, INK, 2)
    # Kicker strip.
    c.fill_rect(x + 2, y + 2, w - 4, 26, story["accent"])
    c.draw_text(x + 12, y + 9, story["kicker"], WHITE, 2, bold=True)
    # Scene.
    scene_top = y + 28
    scene_h = 118
    story["scene"](c, x + 2, scene_top, w - 4, scene_h)
    c.hline(x + 2, scene_top + scene_h, w - 4, INK, 2)
    # Headline, wrapped at scale 2 bold.
    text_top = scene_top + scene_h + 10
    head_lines = wrap_text(story["headline"], w - 24, 2)
    ty = text_top
    for line in head_lines:
        c.draw_text(x + 12, ty, line, INK, 2, bold=True)
        ty += 18
    # Body, wrapped at scale 2.
    body_lines = wrap_text(story["body"], w - 24, 2)
    for line in body_lines:
        c.draw_text(x + 12, ty, line, INK, 2)
        ty += 16


def draw_front_page():
    width, height = 1024, 1024
    c = Canvas(width, height, PAPER)

    # Header band.
    c.fill_rect(0, 0, width, 118, NAVY)
    c.draw_text_centered(0, 10, width, "THE WORLD IN ONE DAY",
                         GOLD, 2, bold=True)
    c.draw_text_centered(0, 38, width, "TUESDAY 17 NOVEMBER 2026",
                         WHITE, 4, bold=True)
    c.draw_text_centered(0, 90, width,
                         "SIX STORIES FROM AROUND THE GLOBE",
                         WHITE, 2)
    c.fill_rect(0, 118, width, 4, GOLD)

    # Six panels: two columns, three rows.
    margin, gap = 12, 12
    panel_w = (width - 2 * margin - gap) // 2
    panel_h = 264
    top = 134
    for i, story in enumerate(STORIES):
        col = i % 2
        row = i // 2
        px = margin + col * (panel_w + gap)
        py = top + row * (panel_h + gap)
        draw_panel(c, px, py, panel_w, panel_h, story)

    # Footer ticker.
    fy = top + 3 * panel_h + 2 * gap + 8
    c.fill_rect(0, fy, width, 40, INK)
    c.draw_text_centered(0, fy + 13, width, FOOTER, WHITE, 2)
    return c


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    canvas = draw_front_page()
    png = encode_png(canvas)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()

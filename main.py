#!/usr/bin/env python3
"""Round 3 entry for make.fun news-image-20261123.

Sums up the world news of Monday 23 November 2026 in one 1024x1024
newspaper front page. Python 3.13 standard library only: own PNG encoder,
own 5x7 bitmap font, no network, no randomness, no clock. Running the
program twice writes byte-identical output.

Layout (all type at scale >= 4, i.e. >= 28 px glyph height):
  masthead  "THE WORLD IN ONE DAY" / "MONDAY 23 NOVEMBER 2026"
  lead      Iran / Strait of Hormuz tanker attacks (full width, ~45%)
  panels    Nvidia / COP31 / South Korea / SpaceX (2x2, distinct tints)
  footer    Molly Meldrum dies, 83 / Hasina faces jail if she returns
"""

import hashlib
import os
import struct
import sys
import zlib

W = 1024
H = 1024

PAPER = (250, 247, 240)
INK = (20, 20, 20)
RED = (178, 32, 32)
SEA = (38, 74, 96)
TINT_GREEN = (232, 240, 228)
TINT_SAND = (242, 232, 213)
TINT_TEAL = (221, 237, 234)
TINT_GREY = (237, 230, 222)
WHITE = (250, 247, 240)

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 cells, '#' = ink. Uppercase + digits + punctuation.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    '+': ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
}


def text_width(text, scale):
    """Pixel width of a line at the given scale (6 px advance per glyph)."""
    return len(text) * 6 * scale - scale


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        for i in range(w * h):
            self.px[i * 3:i * 3 + 3] = bytes(bg)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def hline(self, x, y, w, t, color):
        self.rect(x, y, w, t, color)

    def vline(self, x, y, h, t, color):
        self.rect(x, y, t, h, color)

    def poly(self, points, color):
        """Scanline fill of a simple polygon (list of (x, y))."""
        if not points:
            return
        ys = [p[1] for p in points]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(points)
            for i in range(n):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                if y1 == y2:
                    continue
                if (y1 <= y < y2) or (y2 <= y < y1):
                    t = (y - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                for x in range(int(xs[j]), int(xs[j + 1]) + 1):
                    self.set(x, y, color)

    def circle(self, cx, cy, r, color, fill=True, t=4):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if fill:
                    if d2 <= r * r:
                        self.set(x, y, color)
                else:
                    if (r - t) ** 2 <= d2 <= r * r:
                        self.set(x, y, color)

    def line(self, x1, y1, x2, y2, t, color):
        """Thick straight line (Bresenham + square brush)."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        x, y = x1, y1
        half = t // 2
        while True:
            self.rect(x - half, y - half, t, t, color)
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def text(self, x, y, s, scale, color):
        for ci, ch in enumerate(s):
            glyph = FONT.get(ch)
            if glyph is None:
                raise ValueError("no glyph for %r" % ch)
            ox = x + ci * 6 * scale
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == '1':
                        self.rect(ox + col * scale, y + row * scale,
                                  scale, scale, color)


def draw_text_checked(cv, x, y, s, scale, color, max_w):
    w = text_width(s, scale)
    if w > max_w:
        raise SystemExit("TEXT OVERFLOW: %r width %d > %d" % (s, w, max_w))
    cv.text(x, y, s, scale, color)


# ---------------------------------------------------------------- pictograms
def draw_tanker(cv, x0, y0, x1, y1):
    """Big tanker with a red flame above its stack, on a sea band."""
    # sky is paper; sea band along the bottom of the art box
    sea_y = y1 - 90
    cv.rect(x0, sea_y, x1 - x0, y1 - sea_y, SEA)
    # waves: three light bars in the sea
    for i, wy in enumerate((sea_y + 18, sea_y + 44, sea_y + 70)):
        cv.hline(x0 + 14 + i * 22, wy, x1 - x0 - 28 - i * 22, 6, WHITE)
    # hull: trapezoid, bow to the right
    cv.poly([(x0 + 20, sea_y - 58), (x1 - 30, sea_y - 58),
             (x1 - 70, sea_y + 6), (x0 + 44, sea_y + 6)], INK)
    # deck line and deckhouse
    cv.hline(x0 + 20, sea_y - 58, x1 - 50, 6, INK)
    cv.rect(x0 + 44, sea_y - 118, 96, 60, INK)
    cv.rect(x0 + 60, sea_y - 108, 20, 16, PAPER)
    cv.rect(x0 + 96, sea_y - 108, 20, 16, PAPER)
    # funnel / stack
    cv.rect(x0 + 170, sea_y - 150, 40, 92, INK)
    # red flame bursting above the stack
    fx = x0 + 190
    fy = sea_y - 150
    cv.poly([(fx - 52, fy), (fx - 18, fy - 46), (fx - 4, fy - 12),
             (fx + 12, fy - 78), (fx + 26, fy - 18), (fx + 52, fy - 44),
             (fx + 40, fy)], RED)
    cv.poly([(fx - 26, fy), (fx - 8, fy - 30), (fx + 8, fy - 8),
             (fx + 26, fy - 26), (fx + 22, fy)], (255, 120, 60))
    # smoke puffs drifting left
    cv.circle(x0 + 130, sea_y - 190, 16, INK)
    cv.circle(x0 + 96, sea_y - 216, 12, INK)


def draw_chip(cv, cx, cy):
    """Microchip with a rising chart arrow (Nvidia)."""
    s = 34
    cv.rect(cx - s, cy - s, 2 * s, 2 * s, INK)
    cv.rect(cx - s + 6, cy - s + 6, 2 * s - 12, 2 * s - 12, PAPER)
    cv.rect(cx - 14, cy - 14, 28, 28, INK)
    for i in (-1, 0, 1):
        cv.rect(cx + i * 20 - 3, cy - s - 14, 6, 14, INK)
        cv.rect(cx + i * 20 - 3, cy + s, 6, 14, INK)
        cv.rect(cx - s - 14, cy + i * 20 - 3, 14, 6, INK)
        cv.rect(cx + s, cy + i * 20 - 3, 14, 6, INK)
    # rising arrow over the chip
    cv.line(cx - 30, cy + 26, cx - 8, cy + 2, 6, (34, 110, 60))
    cv.line(cx - 8, cy + 2, cx + 12, cy + 12, 6, (34, 110, 60))
    cv.line(cx + 12, cy + 12, cx + 32, cy - 26, 6, (34, 110, 60))
    cv.poly([(cx + 32, cy - 26), (cx + 14, cy - 26), (cx + 32, cy - 8)],
            (34, 110, 60))


def draw_globe(cv, cx, cy):
    """Globe with a slash (COP31: no deal)."""
    cv.circle(cx, cy, 44, INK, fill=False, t=5)
    cv.hline(cx - 40, cy - 14, 80, 4, INK)
    cv.hline(cx - 42, cy + 12, 84, 4, INK)
    cv.line(cx - 34, cy + 34, cx + 34, cy - 34, 7, INK)


def draw_pencil(cv, cx, cy):
    """Diagonal pencil (South Korea: exam rules)."""
    cv.poly([(cx - 34, cy + 26), (cx + 22, cy - 30), (cx + 34, cy - 18),
             (cx - 22, cy + 38)], INK)
    cv.poly([(cx - 34, cy + 26), (cx - 46, cy + 34), (cx - 22, cy + 38)],
            (200, 170, 120))
    cv.poly([(cx + 22, cy - 30), (cx + 34, cy - 18), (cx + 40, cy - 30),
             (cx + 28, cy - 42)], RED)
    cv.hline(cx - 40, cy + 48, 80, 5, INK)


def draw_scales(cv, cx, cy):
    """Scales of justice (SpaceX sued)."""
    cv.vline(cx, cy - 44, 88, 6, INK)
    cv.hline(cx - 40, cy - 44, 80, 6, INK)
    cv.hline(cx - 22, cy + 44, 44, 6, INK)
    for sx in (cx - 40, cx + 40):
        cv.line(sx, cy - 44, sx - 16, cy + 14, 4, INK)
        cv.line(sx, cy - 44, sx + 16, cy + 14, 4, INK)
        cv.poly([(sx - 20, cy + 14), (sx + 20, cy + 14),
                 (sx, cy + 34)], INK)
    cv.circle(cx, cy - 48, 8, INK)


# -------------------------------------------------------------------- render
def render():
    cv = Canvas(W, H, PAPER)

    # ---- masthead
    title = "THE WORLD IN ONE DAY"
    date = "MONDAY 23 NOVEMBER 2026"
    draw_text_checked(cv, (W - text_width(title, 5)) // 2, 22, title, 5,
                      INK, W - 64)
    draw_text_checked(cv, (W - text_width(date, 6)) // 2, 66, date, 6,
                      INK, W - 64)
    cv.hline(32, 122, W - 64, 6, RED)

    # ---- lead: Iran / Hormuz
    LX, LW = 32, 528
    draw_text_checked(cv, LX, 148, "STRAIT OF HORMUZ", 4, RED, LW)
    for i, line in enumerate(("TANKERS", "BURN IN", "HORMUZ")):
        draw_text_checked(cv, LX, 190 + i * 64, line, 8, INK, LW)
    for i, line in enumerate(("THREE TANKERS HIT", "MINES ON MONDAY.",
                              "ATTACKS AT WAR HIGH.")):
        draw_text_checked(cv, LX, 400 + i * 34, line, 4, INK, LW)
    draw_tanker(cv, 592, 148, 992, 580)
    cv.hline(32, 600, W - 64, 4, INK)

    # ---- panels 2x2
    panels = [
        # (x, y, tint, icon, headline lines, dek lines)
        (32, 612, TINT_GREEN, draw_chip,
         ("HUANG", "BACK +31%"),
         ("NVIDIA BRINGS", "ITS CEO BACK.")),
        (520, 612, TINT_SAND, draw_globe,
         ("COP31", "NO DEAL"),
         ("SUMMIT FAILS", "IN TURKEY.")),
        (32, 778, TINT_TEAL, draw_pencil,
         ("MINISTER", "QUITS"),
         ("OVER AI EXAM", "CHEATING ROW.")),
        (520, 778, TINT_GREY, draw_scales,
         ("SPACEX", "SUED"),
         ("2 STATES SUE", "OVER GROK.")),
    ]
    for (px, py, tint, icon, head, dek) in panels:
        cv.rect(px, py, 472, 156, tint)
        cv.rect(px, py, 472, 156, INK)  # placeholder replaced below
        cv.rect(px + 3, py + 3, 466, 150, tint)
        icon(cv, px + 66, py + 78)
        tx = px + 132
        for i, line in enumerate(head):
            draw_text_checked(cv, tx, py + 10 + i * 42, line, 5, INK, 328)
        for i, line in enumerate(dek):
            draw_text_checked(cv, tx, py + 94 + i * 32, line, 4, INK, 328)

    # ---- footer strip
    cv.rect(32, 946, 8, 58, RED)
    draw_text_checked(cv, 52, 946, "ALSO: MOLLY MELDRUM DIES, 83", 4, INK,
                      W - 84)
    draw_text_checked(cv, 52, 976, "HASINA FACES JAIL IF SHE RETURNS", 4,
                      INK, W - 84)

    return cv.px


def png_bytes(rgb, w, h):
    raw = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3]
                   for y in range(h))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def main():
    data = png_bytes(render(), W, H)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes) sha256 %s"
          % (path, len(data), hashlib.sha256(data).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

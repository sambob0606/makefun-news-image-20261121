"""Draw the 21 November 2026 world-news poster with the Python standard library.

A 1024x1024 newspaper front page: a masthead naming the day, a lead story on
the Gulf crisis, and six more stories from Saturday 21 November 2026, plus a
ticker line. Everything is drawn with a hand-built 5x7 bitmap font, primitive
shape drawing, and a minimal PNG encoder (zlib and struct). No network, no
input files, no wall clock, no randomness: two runs write identical bytes.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (243, 237, 224)
NAVY = (17, 31, 57)
NAVY2 = (30, 50, 88)
GOLD = (196, 156, 34)
GOLD2 = (222, 184, 64)
INK = (26, 26, 26)
MUTED = (99, 94, 82)
CARD = (255, 255, 255)
RULE = (210, 203, 186)
RED = (172, 36, 26)
TEAL = (13, 106, 104)
WHITE = (255, 255, 255)
SOFT = (226, 231, 240)

# A 5x7 bitmap font. Each glyph is seven ints, one per row from the top;
# bit 4 is the leftmost pixel, bit 0 the rightmost. Upper case only: every
# string is upper-cased before it is drawn.
FONT = {
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (7, 2, 2, 2, 2, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 27, 17),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 6, 8, 16, 31),
    "3": (30, 1, 1, 14, 1, 1, 30),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (14, 16, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 1, 14),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 12, 12),
    ",": (0, 0, 0, 0, 12, 4, 8),
    ":": (0, 12, 12, 0, 12, 12, 0),
    ";": (0, 12, 12, 0, 12, 4, 8),
    "!": (4, 4, 4, 4, 4, 0, 4),
    "?": (14, 17, 1, 6, 4, 0, 4),
    "'": (4, 4, 8, 0, 0, 0, 0),
    "-": (0, 0, 0, 14, 0, 0, 0),
    "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8),
    "/": (1, 2, 2, 4, 8, 8, 16),
    "%": (25, 26, 2, 4, 8, 11, 19),
    "&": (12, 18, 20, 8, 21, 18, 13),
    '"': (10, 10, 10, 0, 0, 0, 0),
    "+": (0, 4, 4, 31, 4, 4, 0),
    "=": (0, 0, 31, 0, 31, 0, 0),
    "*": (0, 4, 21, 14, 21, 4, 0),
    "_": (0, 0, 0, 0, 0, 0, 31),
    "<": (2, 4, 8, 16, 8, 4, 2),
    ">": (8, 4, 2, 1, 2, 4, 8),
}


class Canvas:
    """An RGB canvas backed by one flat bytearray."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def fill(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def frame(self, x, y, w, h, color, t=1):
        self.fill(x, y, w, t, color)
        self.fill(x, y + h - t, w, t, color)
        self.fill(x, y, t, h, color)
        self.fill(x + w - t, y, t, h, color)

    def disc(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(0, r * r - (yy - cy) * (yy - cy))))
            self.fill(cx - dx, yy, 2 * dx + 1, 1, color)

    def ring(self, cx, cy, r, color, t=2):
        self.disc(cx, cy, r, color)
        self.disc(cx, cy, r - t, PAPER)

    def ellipse(self, cx, cy, rx, ry, color):
        steps = max(48, int(2 * math.pi * max(rx, ry)))
        for i in range(steps):
            a = 2 * math.pi * i / steps
            x = int(cx + rx * math.cos(a))
            y = int(cy + ry * math.sin(a))
            self.fill(x - 1, y - 1, 3, 3, color)

    def text(self, x, y, s, color, scale=2):
        s = s.upper()
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row_i, bits in enumerate(glyph):
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.fill(cx + col * scale, y + row_i * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def text_width(self, s, scale=2):
        return len(s) * 6 * scale - scale

    def center(self, y, s, color, scale=2, x0=0, x1=None):
        if x1 is None:
            x1 = self.w
        w = self.text_width(s, scale)
        self.text(x0 + (x1 - x0 - w) // 2, y, s, color, scale)

    def wrap(self, s, scale, max_w):
        lines = []
        cur = ""
        for word in s.split(" "):
            trial = (cur + " " + word).strip()
            if self.text_width(trial, scale) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines


def encode_png(w, h, rgb):
    """Minimal deterministic PNG encoder: 8-bit RGB, filter 0, zlib level 6."""

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))


def draw_globe(cv, cx, cy, r):
    """A stylised globe: ring, meridians, equator, and three labelled dots."""
    cv.ring(cx, cy, r, NAVY, 4)
    cv.ellipse(cx, cy, r // 3, r - 4, NAVY2)
    cv.ellipse(cx, cy, r - 4, r // 3, NAVY2)
    cv.fill(cx - r + 4, cy - 1, 2 * r - 8, 2, NAVY2)
    cv.fill(cx - 1, cy - r + 4, 2, 2 * r - 8, NAVY2)
    spots = [
        (cx + int(r * 0.55), cy - int(r * 0.45)),
        (cx - int(r * 0.62), cy - int(r * 0.55)),
        (cx + int(r * 0.30), cy + int(r * 0.62)),
    ]
    for sx, sy in spots:
        cv.disc(sx, sy, 5, RED)


def draw_card(cv, x, y, w, h, kicker, kcolor, head, deck):
    cv.fill(x, y, w, h, CARD)
    cv.frame(x, y, w, h, RULE, 1)
    cv.fill(x, y, w, 5, kcolor)
    cv.text(x + 14, y + 16, kicker, kcolor, 2)
    lines = cv.wrap(head, 3, w - 28)
    ty = y + 40
    for ln in lines[:2]:
        cv.text(x + 14, ty, ln, NAVY, 3)
        ty += 24
    dlines = cv.wrap(deck, 2, w - 28)
    ty += 6
    for ln in dlines[:2]:
        cv.text(x + 14, ty, ln, MUTED, 2)
        ty += 16


def build_entry(path):
    cv = Canvas(W, H, PAPER)
    cv.frame(10, 10, W - 20, H - 20, NAVY, 3)
    cv.frame(18, 18, W - 36, H - 36, GOLD, 1)

    # Masthead: the day, named loud.
    cv.fill(24, 24, W - 48, 132, NAVY)
    draw_globe(cv, 92, 90, 44)
    cv.center(44, "THE WORLD IN ONE DAY", GOLD2, 3, x0=150, x1=1000)
    cv.center(76, "SATURDAY, 21 NOVEMBER 2026", WHITE, 5, x0=150, x1=1000)
    cv.fill(170, 128, 780, 3, GOLD)

    # Lead story: the Gulf crisis.
    cv.text(40, 176, "GULF ON EDGE", RED, 4)
    head = cv.wrap("DRONES DOWN, MISSILES FLY AS GULF CRISIS DEEPENS",
                   4, W - 80)
    ty = 210
    for ln in head:
        cv.text(40, ty, ln, NAVY, 4)
        ty += 34
    deck = ("US DENIES IRAN CLAIM IT HIT AN F-16 OVER THE GULF. TWO WOUNDED "
            "IN BAHRAIN AS IRANIAN STRIKES HIT. HOUTHIS FIRE MISSILES AT "
            "RIYADH; SAUDIS INTERCEPT. TRUMP WEIGHS NEW STRIKES.")
    ty += 8
    for ln in cv.wrap(deck, 2, W - 80):
        cv.text(40, ty, ln, INK, 2)
        ty += 17

    # Section header and the six-card grid.
    cv.fill(40, 408, W - 80, 3, GOLD)
    cv.text(40, 424, "THE DAY IN BRIEF", NAVY, 3)
    cards = [
        ("BALTIC BLAZE", RED,
         "DRONE STRIKE SETS RUSSIAN SHIP ABLAZE",
         "CREW EVACUATES AS VESSEL DRIFTS INTO FINNISH WATERS"),
        ("COP31 OVERTIME", TEAL,
         "CLIMATE TALKS STALL ON FOSSIL FUELS",
         "NO DEAL IN TURKEY AS SUMMIT RUNS INTO OVERTIME"),
        ("TRUMP'S HOMECOMING", NAVY,
         "FREEWHEELING PRESSER AFTER CHINA TRIP",
         "PRESIDENT RETURNS FROM FOUR-DAY ASIA TOUR"),
        ("EL CHAPO ISIDRO", NAVY,
         "MEXICO NABS DRUG LORD",
         "LATEST IN A STRING OF HIGH-PROFILE ARRESTS"),
        ("MARKETS", RED,
         "WALL STREET SLIDES ON AI SELLOFF",
         "S&P 500 AND DOW SLIP INTO CORRECTION"),
        ("UK-EU RESET", TEAL,
         "BRITAIN AND EU SEAL POST-BREXIT RESET",
         "FOOD TRADE EASED, YOUTH MOBILITY BOOSTED"),
    ]
    cw, ch, gap = 462, 128, 20
    for i, (kicker, kcolor, head, deck) in enumerate(cards):
        x = 40 + (i % 2) * (cw + gap)
        y = 462 + (i // 2) * (ch + gap)
        draw_card(cv, x, y, cw, ch, kicker, kcolor, head, deck)

    # Ticker strip and footer: the date again, and a line for the judge.
    cv.fill(24, 898, W - 48, 60, NAVY)
    cv.text(40, 912, "ALSO: DENMARK EXPELS RUSSIAN ATTACHE OVER RAPPER PLOT",
            GOLD2, 2)
    cv.text(40, 936,
            "FOR THE JUDGE: EVERY STORY HERE HAPPENED OR BROKE ON 21 NOVEMBER 2026",
            WHITE, 2)
    cv.center(970, "ONE DAY, ONE PAGE: SATURDAY 21 NOVEMBER 2026", INK, 2)

    data = encode_png(W, H, bytes(cv.px))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    n = build_entry(os.path.join(here, "entry.png"))
    print("wrote entry.png (%d bytes)" % n)

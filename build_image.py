"""Fresh raster renderer for the 23 November 2026 world-news poster.

Draws a 1024x1024 PNG with only the Python standard library: a small
5x7 bitmap font, flat geometric pictograms, and a hand-rolled PNG
encoder. No network, no photos, no timestamps anywhere in the output,
so two runs produce byte-identical files.
"""

import struct
import zlib

# ---------------------------------------------------------------- canvas

PAPER = (247, 243, 234)
CARD = (255, 255, 255)
INK = (20, 32, 52)
GOLD = (198, 148, 28)
TEAL = (13, 110, 102)
RUST = (172, 56, 30)
BLUE = (36, 82, 148)
PLUM = (104, 58, 118)
GREEN = (44, 118, 58)
AMBER = (184, 116, 18)


class Sheet:
    """An RGB pixel buffer with simple flat-colour drawing helpers."""

    def __init__(self, width, height, colour):
        self.width = width
        self.height = height
        buf = bytearray(width * height * 3)
        for i in range(width * height):
            buf[3 * i] = colour[0]
            buf[3 * i + 1] = colour[1]
            buf[3 * i + 2] = colour[2]
        self.pixels = buf

    def dot(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = 3 * (y * self.width + x)
            self.pixels[i] = colour[0]
            self.pixels[i + 1] = colour[1]
            self.pixels[i + 2] = colour[2]

    def block(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        for yy in range(y0, y1):
            base = 3 * (yy * self.width + x0)
            for xx in range(x0, x1):
                i = base + 3 * (xx - x0)
                self.pixels[i] = colour[0]
                self.pixels[i + 1] = colour[1]
                self.pixels[i + 2] = colour[2]

    def frame(self, x, y, w, h, colour, thick=2):
        self.block(x, y, w, thick, colour)
        self.block(x, y + h - thick, w, thick, colour)
        self.block(x, y, thick, h, colour)
        self.block(x + w - thick, y, thick, h, colour)

    def disc(self, cx, cy, r, colour):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) * (yy - cy)) ** 0.5)
            self.block(cx - dx, yy, 2 * dx + 1, 1, colour)

    def ring(self, cx, cy, r, colour, thick=3):
        for yy in range(cy - r, cy + r + 1):
            dy = yy - cy
            outer = int((r * r - dy * dy) ** 0.5)
            inner2 = (r - thick) * (r - thick) - dy * dy
            inner = int(inner2 ** 0.5) if inner2 > 0 else 0
            self.block(cx - outer, yy, outer - inner, 1, colour)
            self.block(cx + inner, yy, outer - inner + 1, 1, colour)

    def stroke(self, x0, y0, x1, y1, colour, thick=1):
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            self.block(x - thick // 2, y - thick // 2, thick, thick, colour)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def poly(self, points, colour):
        """Fill a polygon with a scanline pass."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for yy in range(min(ys), max(ys) + 1):
            nodes = []
            n = len(points)
            for k in range(n):
                x0, y0 = points[k]
                x1, y1 = points[(k + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    nodes.append(x0 + (yy - y0) * (x1 - x0) / (y1 - y0))
            nodes.sort()
            for k in range(0, len(nodes) - 1, 2):
                self.block(int(nodes[k]), yy, int(nodes[k + 1]) - int(nodes[k]) + 1, 1, colour)


# ---------------------------------------------------------------- font
# 5x7 bitmap font, uppercase + digits + punctuation. Each glyph is seven
# rows; each row is a 5-bit number, bit 4 is the leftmost pixel.

GLYPHS = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x0E, 0x10, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E),
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    ",": (0x00, 0x00, 0x00, 0x00, 0x0C, 0x04, 0x08),
    ":": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ";": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x04, 0x08),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    "-": (0x00, 0x00, 0x00, 0x0E, 0x00, 0x00, 0x00),
    "+": (0x00, 0x04, 0x04, 0x0E, 0x04, 0x04, 0x00),
    "%": (0x19, 0x1A, 0x02, 0x04, 0x08, 0x0B, 0x13),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "/": (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "=": (0x00, 0x00, 0x0E, 0x00, 0x0E, 0x00, 0x00),
}

CHAR_W = 6  # 5 pixels + 1 pixel gap


def text_width(text, scale):
    return len(text) * CHAR_W * scale - scale


def draw_text(sheet, x, y, text, colour, scale):
    cx = x
    for ch in text.upper():
        glyph = GLYPHS.get(ch, GLYPHS[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    sheet.block(cx + col * scale, y + row * scale, scale, scale, colour)
        cx += CHAR_W * scale
    return cx


def wrap_lines(text, max_width, scale):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_block(sheet, x, y, text, colour, scale, max_width, line_h, max_lines=None):
    lines = wrap_lines(text, max_width, scale)
    if max_lines is not None:
        lines = lines[:max_lines]
    for i, line in enumerate(lines):
        draw_text(sheet, x, y + i * line_h, line, colour, scale)
    return len(lines)


# ---------------------------------------------------------------- pictograms
# Each draws inside an 84x84 box whose top-left corner is (x, y).

def pic_chip(sheet, x, y, accent):
    sheet.block(x + 22, y + 26, 40, 40, INK)
    sheet.block(x + 32, y + 36, 20, 20, PAPER)
    sheet.block(x + 38, y + 42, 8, 8, accent)
    for k in range(3):
        off = 28 + k * 14
        sheet.block(x + off, y + 18, 6, 8, INK)
        sheet.block(x + off, y + 66, 6, 8, INK)
        sheet.block(x + 14, y + off, 8, 6, INK)
        sheet.block(x + 62, y + off, 8, 6, INK)
    sheet.stroke(x + 8, y + 76, x + 30, y + 54, accent, 4)
    sheet.stroke(x + 30, y + 54, x + 48, y + 66, accent, 4)
    sheet.stroke(x + 48, y + 66, x + 72, y + 40, accent, 4)
    sheet.poly([(x + 72, y + 40), (x + 60, y + 40), (x + 72, y + 52)], accent)


def pic_drone(sheet, x, y, accent):
    for dx, dy in ((14, 14), (70, 14), (14, 70), (70, 70)):
        sheet.stroke(x + 42, y + 42, x + dx, y + dy, INK, 3)
        sheet.ring(x + dx, y + dy, 9, INK, 3)
    sheet.disc(x + 42, y + 42, 12, accent)
    sheet.disc(x + 42, y + 42, 5, PAPER)


def pic_ship(sheet, x, y, accent):
    sheet.poly([(x + 10, y + 52), (x + 74, y + 52), (x + 64, y + 70), (x + 20, y + 70)], INK)
    sheet.block(x + 30, y + 34, 24, 18, INK)
    sheet.stroke(x + 42, y + 34, x + 42, y + 16, INK, 4)
    sheet.block(x + 42, y + 16, 14, 8, RUST)
    # Small gold starburst above the mast: the blast of the strike.
    bx, by = x + 49, y + 8
    sheet.stroke(bx - 8, by, bx + 8, by, GOLD, 3)
    sheet.stroke(bx, by - 6, bx, by + 6, GOLD, 3)
    sheet.stroke(bx - 6, by - 5, bx + 6, by + 5, GOLD, 3)
    sheet.stroke(bx - 6, by + 5, bx + 6, by - 5, GOLD, 3)
    for k, wy in enumerate((y + 76, y + 80)):
        sheet.stroke(x + 6, wy, x + 78, wy, BLUE, 3)


def pic_sanction(sheet, x, y, accent):
    sheet.ring(x + 42, y + 42, 32, INK, 4)
    draw_text(sheet, x + 33, y + 30, "$", accent, 3)
    sheet.stroke(x + 18, y + 66, x + 66, y + 18, RUST, 6)


def pic_glove(sheet, x, y, accent):
    # Boxing glove as a padded mitt: square padded body with finger
    # seams, a thumb bump on the side, and a wrist strap below.
    sheet.block(x + 18, y + 12, 42, 42, accent)
    sheet.disc(x + 18, y + 12, 12, accent)
    sheet.disc(x + 60, y + 12, 12, accent)
    sheet.disc(x + 18, y + 54, 12, accent)
    sheet.disc(x + 60, y + 54, 12, accent)
    sheet.disc(x + 66, y + 40, 9, accent)
    sheet.block(x + 32, y + 16, 3, 30, PAPER)
    sheet.block(x + 46, y + 16, 3, 30, PAPER)
    sheet.block(x + 26, y + 58, 30, 12, INK)
    sheet.block(x + 30, y + 61, 22, 2, PAPER)
    sheet.block(x + 30, y + 65, 22, 2, PAPER)


def pic_flag(sheet, x, y, accent):
    sheet.stroke(x + 22, y + 10, x + 22, y + 76, INK, 4)
    sheet.poly([(x + 22, y + 12), (x + 66, y + 22), (x + 22, y + 34)], PAPER)
    sheet.frame(x + 22, y + 12, 44, 22, INK, 2)
    sheet.stroke(x + 30, y + 52, x + 42, y + 64, GREEN, 5)
    sheet.stroke(x + 42, y + 64, x + 66, y + 40, GREEN, 5)


PICTOGRAMS = {
    "chip": pic_chip,
    "drone": pic_drone,
    "ship": pic_ship,
    "sanction": pic_sanction,
    "glove": pic_glove,
    "flag": pic_flag,
}


# ---------------------------------------------------------------- stories

STORIES = [
    {
        "kicker": "TECH - USA",
        "headline": "HUANG BACK AS NVIDIA CEO",
        "body": "Shares jump 31.5% as Jensen Huang returns to lead the chipmaker after the board reinstates him.",
        "pic": "chip",
        "accent": TEAL,
    },
    {
        "kicker": "EUROPE - SECURITY",
        "headline": "RUSSIAN DRONE OVER POLAND",
        "body": "A suspected Russian drone spends eight minutes in Polish airspace during strikes on western Ukraine.",
        "pic": "drone",
        "accent": RUST,
    },
    {
        "kicker": "WAR AT SEA - LIBYA",
        "headline": "UKRAINE SINKS RUSSIAN WARSHIP",
        "body": "Kyiv says naval drones sank a Russian warship in the Libyan port of Benghazi.",
        "pic": "ship",
        "accent": BLUE,
    },
    {
        "kicker": "USA - IRAN",
        "headline": "TRUMP HITS IRAN WITH SANCTIONS",
        "body": "Sweeping new sanctions aim to cut what the Treasury calls the regime's last financial lifeline.",
        "pic": "sanction",
        "accent": AMBER,
    },
    {
        "kicker": "SPORT - BOXING",
        "headline": "FURY REVEALS SCHIZOPHRENIA",
        "body": "Ex-heavyweight champion speaks of his diagnosis in a Netflix film before the Joshua fight.",
        "pic": "glove",
        "accent": PLUM,
    },
    {
        "kicker": "ASIA - DIPLOMACY",
        "headline": "THAI-CAMBODIA TRUCE HOLDS",
        "body": "Fighting pauses on the border after the two countries reach a ceasefire deal on Monday.",
        "pic": "flag",
        "accent": GREEN,
    },
]


# ---------------------------------------------------------------- layout

W, H = 1024, 1024


def draw_header(sheet):
    sheet.block(0, 0, W, 118, INK)
    sheet.block(0, 118, W, 4, GOLD)
    draw_text(sheet, 28, 24, "THE WORLD TODAY", PAPER, 4)
    draw_text(sheet, 28, 74, "MONDAY 23 NOVEMBER 2026", GOLD, 3)
    # Small globe on the right of the masthead.
    gx, gy = 936, 59
    sheet.ring(gx, gy, 36, PAPER, 3)
    sheet.stroke(gx - 36, gy, gx + 36, gy, PAPER, 2)
    sheet.stroke(gx, gy - 36, gx, gy + 36, PAPER, 2)
    sheet.ring(gx, gy, 18, GOLD, 2)


def draw_card(sheet, x, y, w, h, story):
    sheet.block(x, y, w, h, CARD)
    sheet.frame(x, y, w, h, INK, 2)
    sheet.block(x, y, w, 8, story["accent"])
    draw_text(sheet, x + 18, y + 22, story["kicker"], story["accent"], 2)
    PICTOGRAMS[story["pic"]](sheet, x + 18, y + 48, story["accent"])
    draw_block(sheet, x + 116, y + 56, story["headline"], INK, 3, w - 134, 26, max_lines=2)
    draw_block(sheet, x + 18, y + 150, story["body"], (64, 72, 88), 2, w - 36, 18, max_lines=4)


def draw_footer(sheet):
    line = "REPORTED 23 NOV 2026 - BBC - THE GUARDIAN - AL JAZEERA - CNN - REUTERS"
    tw = text_width(line, 2)
    draw_text(sheet, (W - tw) // 2, 990, line, (96, 104, 120), 2)


def render():
    sheet = Sheet(W, H, PAPER)
    draw_header(sheet)
    margin, gap = 24, 16
    cw = (W - 2 * margin - gap) // 2
    ch = (972 - 142 - 2 * gap) // 3
    for i, story in enumerate(STORIES):
        col = i % 2
        row = i // 2
        draw_card(sheet, margin + col * (cw + gap), 142 + row * (ch + gap), cw, ch, story)
    draw_footer(sheet)
    return sheet


# ---------------------------------------------------------------- PNG encode

def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(sheet):
    raw = bytearray()
    stride = sheet.width * 3
    for yy in range(sheet.height):
        raw.append(0)  # filter: none
        start = yy * stride
        raw += sheet.pixels[start:start + stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", sheet.width, sheet.height, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png


def build_png_bytes():
    return encode_png(render())


if __name__ == "__main__":
    import os

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    data = build_png_bytes()
    with open(os.path.join(out_dir, "entry.png"), "wb") as fh:
        fh.write(data)
    print("wrote", os.path.join(out_dir, "entry.png"), len(data), "bytes")

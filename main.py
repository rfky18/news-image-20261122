# Front page for Sunday 22 November 2026 — drawn entirely in code.
# Renders a 1024x1024 newspaper front page summarising the day's world news.
# Stdlib only, no network. Text comes from bitmap atlases rendered at build
# time from real Google Fonts TTFs (Bodoni Moda, Libre Baskerville, Gelasio,
# Liberation Sans, Roboto); all pictures are flat vector shapes drawn here.
import json
import os
import struct
import sys
import zlib

W, H = 1024, 1024
BASE = os.path.dirname(os.path.abspath(__file__))

PAPER = (247, 242, 231)
INK = (26, 26, 26)
RED = (176, 30, 36)
NAVY = (31, 58, 95)
TEAL = (15, 118, 110)
GREY = (90, 90, 88)
LIGHT = (232, 226, 212)
SEA = (207, 227, 236)
LAND = (217, 196, 143)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


# ---------------------------------------------------------------- PNG codec
def _unfilter(raw, w, h, bpp, ctype):
    stride = w * bpp
    out = bytearray()
    prev = bytearray(stride)
    pos = 0
    for _ in range(h):
        f = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out += line
        prev = line
    return bytes(out)


def read_png_gray(path):
    """Return (w, h, bytes) grayscale pixels from an 8-bit PNG."""
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, w, h, bitd, ctype, idat = 8, 0, 0, 0, 0, b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bitd, ctype = struct.unpack(">IIBB", chunk[:10])
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    assert bitd == 8 and ctype in (0, 2, 6), (bitd, ctype)
    bpp = {0: 1, 2: 3, 6: 4}[ctype]
    raw = _unfilter(zlib.decompress(idat), w, h, bpp, ctype)
    if ctype == 0:
        return w, h, raw
    if ctype == 2:
        return w, h, bytes(raw[i] for i in range(0, len(raw), 3))
    return w, h, bytes(raw[i + 3] for i in range(0, len(raw), 4))


def write_png_rgb(path, w, h, px):
    def chunk(typ, payload):
        c = struct.pack(">I", len(payload)) + typ + payload
        return c + struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += px[y * w * 3:(y + 1) * w * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.rect(0, 0, w, h, bg)

    def _set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                self.px[i], self.px[i + 1], self.px[i + 2] = c
                i += 3

    def hline(self, x, y, w, c):
        self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self._set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            dx = int(rx * (t ** 0.5)) if t > 0 else 0
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def poly(self, pts, c):
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / float(y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(int(xs[i]), y, max(1, int(xs[i + 1]) - int(xs[i])), 1, c)

    def star(self, cx, cy, r, c, points=8):
        import math
        pts = []
        for i in range(points * 2):
            ang = math.pi * i / points - math.pi / 2
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((int(cx + rr * math.cos(ang)), int(cy + rr * math.sin(ang))))
        self.poly(pts, c)


# -------------------------------------------------------------------- fonts
class Font:
    def __init__(self, name):
        with open(os.path.join(BASE, "atlas", "atlas_%s.json" % name)) as f:
            m = json.load(f)
        self.ascent, self.descent = m["ascent"], m["descent"]
        self.glyphs = m["glyphs"]
        self.aw, self.ah, self.px = read_png_gray(
            os.path.join(BASE, "atlas", "atlas_%s.png" % name))

    def width(self, text):
        return sum(self.glyphs.get(ch, self.glyphs[" "])[4] for ch in text)

    def draw(self, cv, x, y_baseline, text, color):
        cx = x
        for ch in text:
            g = self.glyphs.get(ch)
            if g is None:
                ch = "?"
                g = self.glyphs.get(ch)
                if g is None:
                    continue
            gx, gy, gw, gh, adv, l, t = g
            if ch != " ":
                dx, dy = cx + l, y_baseline + t
                r, gg, b = color
                for row in range(gh):
                    ay = dy + row
                    if ay < 0 or ay >= cv.h:
                        continue
                    for col in range(gw):
                        a = self.px[(gy + row) * self.aw + gx + col]
                        if a:
                            ax = dx + col
                            if 0 <= ax < cv.w:
                                i = (ay * cv.w + ax) * 3
                                cv.px[i] = (r * a + cv.px[i] * (255 - a)) // 255
                                cv.px[i + 1] = (gg * a + cv.px[i + 1] * (255 - a)) // 255
                                cv.px[i + 2] = (b * a + cv.px[i + 2] * (255 - a)) // 255
            cx += adv
        return cx


FONTS = {}


def F(name):
    if name not in FONTS:
        FONTS[name] = Font(name)
    return FONTS[name]


def wrap(text, font, width):
    lines, cur = [], ""
    for word in text.split(" "):
        trial = (cur + " " + word).strip()
        if font.width(trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_lines(cv, x, y, lines, font, color, lh, align="left", width=None):
    for ln in lines:
        lx = x
        if align == "center" and width is not None:
            lx = x + (width - font.width(ln)) // 2
        elif align == "right" and width is not None:
            lx = x + width - font.width(ln)
        font.draw(cv, lx, y, ln, color)
        y += lh
    return y


def draw_wrapped(cv, x, y, text, font, color, lh, width, max_lines=None):
    lines = wrap(text, font, width)
    if max_lines:
        lines = lines[:max_lines]
    return draw_lines(cv, x, y, lines, font, color, lh)

# ------------------------------------------------------- flat illustrations
def illo_cop31(cv, x, y, w, h):
    cv.rect(x, y, w, h, (127, 179, 168))
    cv.rect(x, y + h - 26, w, 26, (86, 130, 96))
    cv.circle(x + w - 52, y + 26, 17, (250, 226, 140))
    cv.rect(x + 18, y + h - 62, 150, 36, (240, 236, 224))          # hall
    cv.poly([(x + 18, y + h - 62), (x + 93, y + h - 82), (x + 168, y + h - 62)], (176, 30, 36))
    for i in range(5):
        cv.vline(x + 36 + i * 26, y + h - 58, 30, INK)
    # flags
    cols = [(176, 30, 36), (31, 58, 95), (15, 118, 110), (200, 160, 40), (90, 60, 120)]
    for i, c in enumerate(cols):
        fx = x + w - 118 + i * 22
        cv.vline(fx, y + 14, 34, INK)
        cv.rect(fx, y + 14, 16, 10, c)
    cv.rect(x + 8, y + h - 22, 60, 14, (31, 58, 95))
    F("libsb9").draw(cv, x + 12, y + h - 12, "DAY 13", WHITE)


def illo_bahrain(cv, x, y, w, h):
    cv.rect(x, y, w, h, (18, 28, 52))
    for sx, sy in [(30, 14), (90, 26), (150, 10), (210, 22), (260, 12), (300, 28), (60, 40), (180, 36)]:
        cv.circle(x + sx, y + sy, 1, WHITE)
    cv.rect(x, y + h - 22, w, 22, (28, 68, 96))                    # sea
    cv.rect(x + 20, y + h - 52, 90, 30, (52, 58, 66))              # base
    cv.rect(x + 130, y + h - 44, 70, 22, (52, 58, 66))
    for bx in (x + 40, x + 150):
        cv.circle(bx, y + h - 56, 12, (220, 220, 210))
        cv.line(bx, y + h - 56, bx + 16, y + h - 74, (220, 220, 210))
        cv.circle(bx + 16, y + h - 74, 3, (250, 200, 60))
    cv.star(x + w - 46, y + 34, 16, (250, 160, 40))
    cv.star(x + w - 46, y + 34, 8, (250, 220, 120))
    cv.line(x + 30, y + 12, x + w - 60, y + 30, (250, 200, 60))
    cv.line(x + 60, y + 8, x + w - 46, y + 34, (250, 200, 60))
    cv.rect(x + 8, y + h - 20, 74, 12, (176, 30, 36))
    F("libsb9").draw(cv, x + 11, y + h - 11, "2 RADARS", WHITE)


def illo_kyiv(cv, x, y, w, h):
    cv.rect(x, y, w, h, (22, 32, 58))
    for sx, sy in [(40, 16), (120, 10), (200, 20), (280, 12), (70, 30), (240, 32)]:
        cv.circle(x + sx, y + sy, 1, WHITE)
    cv.rect(x, y + h - 34, w, 34, (40, 44, 56))
    cv.rect(x + 24, y + h - 74, 60, 40, (24, 26, 34))              # block
    cv.poly([(x + 24, y + h - 74), (x + 54, y + h - 88), (x + 84, y + h - 74)], (24, 26, 34))
    for wy in range(y + h - 68, y + h - 38, 10):
        for wx in range(x + 32, x + 76, 12):
            cv.rect(wx, wy, 5, 6, (250, 200, 60))
    cv.rect(x + 200, y + h - 60, 70, 26, (24, 26, 34))
    # drones + intercepts
    for dx, dy in [(150, 26), (190, 44), (230, 22), (270, 46)]:
        cv.rect(x + dx - 6, y + dy - 2, 12, 4, (200, 200, 190))
        cv.circle(x + dx, y + dy, 2, (250, 60, 40))
    cv.star(x + 150, y + 52, 9, (250, 200, 60))
    cv.star(x + 240, y + 58, 7, (250, 200, 60))
    cv.rect(x + 8, y + h - 20, 92, 12, (176, 30, 36))
    F("libsb9").draw(cv, x + 11, y + h - 11, "161 DOWNED", WHITE)


def illo_small(cv, x, y, w, h, kind):
    bg = {
        "vote": (15, 118, 110), "f1": (24, 26, 34), "cricket": (34, 120, 60),
        "ship": (28, 68, 120), "power": (200, 160, 40), "health": (240, 236, 224),
        "cyber": (31, 58, 95), "plane": (127, 179, 200), "bottle": (90, 60, 60),
        "gaza": (200, 180, 120),
    }[kind]
    cv.rect(x, y, w, h, bg)
    if kind == "vote":
        cv.rect(x + w // 2 - 14, y + 8, 28, 18, WHITE)
        cv.rect(x + w // 2 - 8, y + 8, 16, 3, RED)
        cv.line(x + w // 2 - 20, y + 26, x + w // 2 - 8, y + 12, RED)
    elif kind == "f1":
        for i in range(8):
            cv.rect(x + i * 12, y + 4, 6, 5, WHITE if i % 2 == 0 else BLACK)
        cv.rect(x + 30, y + 16, 46, 8, (200, 30, 30))
        cv.circle(x + 40, y + 26, 4, BLACK)
        cv.circle(x + 66, y + 26, 4, BLACK)
    elif kind == "cricket":
        cv.line(x + 20, y + 6, x + 60, y + 26, (220, 180, 120))
        cv.circle(x + 78, y + 10, 4, (250, 240, 220))
        cv.rect(x + 90, y + 20, 60, 3, WHITE)
    elif kind == "ship":
        cv.rect(x + 20, y + 16, 70, 9, (40, 40, 44))
        cv.rect(x + 44, y + 6, 8, 10, (200, 200, 200))
        cv.star(x + 96, y + 10, 7, (250, 140, 30))
        cv.rect(x, y + 25, w, 5, (200, 220, 235))
    elif kind == "power":
        cv.line(x + 30, y + 28, x + 40, y + 4, INK)
        cv.line(x + 50, y + 28, x + 40, y + 4, INK)
        cv.line(x + 30, y + 14, x + 50, y + 14, INK)
        cv.line(x + 40, y + 4, x + 80, y + 10, (250, 220, 60))
        cv.circle(x + 84, y + 11, 3, (250, 220, 60))
    elif kind == "health":
        cv.rect(x + w // 2 - 4, y + 5, 8, 22, RED)
        cv.rect(x + w // 2 - 13, y + 12, 26, 8, RED)
    elif kind == "cyber":
        cv.poly([(x + w // 2, y + 4), (x + w // 2 + 12, y + 10), (x + w // 2 + 8, y + 24),
                 (x + w // 2, y + 28), (x + w // 2 - 8, y + 24), (x + w // 2 - 12, y + 10)],
                (220, 220, 210))
        F("libsb9").draw(cv, x + w // 2 - 4, y + 20, "!", NAVY)
    elif kind == "plane":
        cv.rect(x + 20, y + 12, 60, 7, WHITE)
        cv.poly([(x + 80, y + 12), (x + 98, y + 16), (x + 80, y + 19)], WHITE)
        cv.rect(x + 44, y + 4, 5, 8, WHITE)
        cv.rect(x + 110, y + 24, 50, 3, (31, 58, 95))
    elif kind == "bottle":
        cv.rect(x + w // 2 - 7, y + 6, 14, 20, (60, 30, 30))
        cv.rect(x + w // 2 - 3, y + 2, 6, 5, (60, 30, 30))
        cv.rect(x + w // 2 - 7, y + 14, 14, 4, (250, 240, 220))
    elif kind == "gaza":
        cv.rect(x + 20, y + 14, 56, 10, WHITE)
        cv.rect(x + 76, y + 16, 20, 8, (200, 200, 200))
        cv.circle(x + 34, y + 26, 4, BLACK)
        cv.circle(x + 64, y + 26, 4, BLACK)
        cv.circle(x + 86, y + 26, 4, BLACK)

# -------------------------------------------------------------------- layout
M = 14
CW = W - 2 * M

HEROES = [
    dict(illo=illo_cop31, banner="COP31: FINAL TEXT AT DAWN", badge="ONGOING",
         badge_bg=WHITE, badge_fg=RED, kicker="ANTALYA · TÜRKIYE — CLIMATE",
         headline="COP31's final text lands at dawn — with no mention of fossil fuels",
         deck="The 10-page text recalls the Dubai pact, keeps a 35% clean-power goal for 2035, drops a $120bn adaptation target and is the first to admit the world will overshoot 1.5°C. Objections closed at 03:00 GMT; no deal yet at press time.",
         source="BBC · Reuters · The Guardian"),
    dict(illo=illo_bahrain, banner="IRAN CLAIMS STRIKES ON US BASES", badge="CLAIM",
         badge_bg=(250, 200, 60), badge_fg=INK, kicker="MANAMA · BAHRAIN — GULF WAR",
         headline="Iran claims strikes on US bases in Bahrain; Bahrain denies hits",
         deck="The IRGC says missiles and drones hit two Patriot radars at al-Riffa and Awali Sakir. Bahrain says its defences intercepted the attack; one facility burned, no casualties; two tankers were hit near Khasab. Hits on US positions are unconfirmed.",
         source="Al Jazeera · Reuters · IRGC statement"),
    dict(illo=illo_kyiv, banner="186 DRONES, 161 DOWNED", badge="REPORTED",
         badge_bg=WHITE, badge_fg=NAVY, kicker="KYIV · UKRAINE — WAR",
         headline="Russia's overnight barrage: 186 drones, 161 downed",
         deck="Moscow fired 186 drones and three ballistic missiles overnight; defences shot down or jammed 161. Strikes were recorded at 18 sites; a five-storey block in the Kyiv region was destroyed, with up to seven feared trapped and two hurt.",
         source="Ukrainian Air Force · Kyiv Independent"),
]

SECONDARY = [
    ("HONG KONG · ELECTION", TEAL, "vote", "Hong Kong elects its Election Committee",
     "856 candidates for 723 seats; 5,700 voters; turnout 93.55% by 14:00.", "SCMP"),
    ("LAS VEGAS · FORMULA 1", (24, 26, 34), "f1", "Verstappen wins the Las Vegas GP",
     "Pole to flag; Norris 2nd, Piastri 3rd from 17th; Russell hits the wall late.", "Reuters · F1"),
    ("WELLINGTON · CRICKET", (34, 120, 60), "cricket", "India declare 720/9 — a record in NZ",
     "Rahul 136, Pant 128; the highest Test total ever in New Zealand.", "Reuters · AP"),
    ("GULF OF FINLAND · WAR", (28, 68, 120), "ship", "Sparta II still ablaze off Finland",
     "Russian freighter hit by a drone on Saturday, still burning at anchor off Loviisa; 16 crew safe.", "Reuters"),
    ("TEHRAN · ENERGY", (200, 160, 40), "power", "Iran begins rationing electricity",
     "Rolling cuts of up to two hours a day as war damage cuts gas supply.", "AP"),
    ("BRASÍLIA · HEALTH", (176, 30, 36), "health", "Bolsonaro in intensive care",
     "Acute bowel obstruction, 71, stable; his son says surgery is possible.", "Reuters"),
    ("WASHINGTON · CYBER", NAVY, "cyber", "FBI probes a hack of its crime database",
     "NCIC database breached; second breach in two months; Washington State pauses gun-dealer checks.", "AP"),
    ("BRUSSELS · LABOUR", (31, 58, 95), "plane", "Belgium grounds Monday's flights for a strike",
     "Air-traffic controllers join a national strike over savings; most flights 07:00–21:00 cancelled.", "Xinhua"),
    ("MANIPUR · HEALTH", (90, 60, 60), "bottle", "Toxic-liquor toll in Manipur climbs to 19",
     "About 600 treated, six arrested.", "NDTV"),
    ("GAZA CITY · GAZA", (176, 140, 60), "gaza", "Four killed as Israeli fire hits Gaza",
     "Drone strike on a food-aid vehicle kills three in Tel al-Hawa; one more shot in Jabalia.", "AFP"),
]

ALSO = [
    "Nvidia faces an SEC probe (Straits Times · CNBC)",
    "Zverev meets Alcaraz for the ATP crown (ATP)",
    "Liverpool host Man United — Pochettino's debut (Sky Sports)",
    "Zelenskyy defends Crimean Bridge strikes (BBC)",
    'Beijing "firmly opposes" US ban on its carriers (Reuters)',
    "Marles rejects US report on AUKUS subs (Reuters)",
    "Nepal PM lands in Delhi on first state visit (IANS)",
    "Denmark expels Russian attaché over alleged plot (Guardian)",
    "Estonia to shut Russia border from 1 Dec (Reuters)",
    "Saudi downs Houthi missile aimed at Riyadh (Anadolu)",
    "Sudan army retakes ~30 towns in Kordofan (FT)",
    "RSF accused of West Kordofan killings (Claim)",
    "Somalia expels UAE ambassador, recalls envoy (Wires)",
    "Kenya discharges its last Ebola patient (Wires)",
    "Philippines M5.9 quake deep below Palawan (EMSC)",
    "Chinese bomber turns back 170 km from Manila (AP)",
    "Taiwan holds live-fire drill on Kinmen (CNA)",
    "Japan poll: record 92% friendly to South Korea (JKN)",
    "Candy-factory fire in Serang: 3 dead, 36 missing (Detiknews)",
    "Bayelsa boat toll rises to 26 (RIA · Vanguard)",
    "Trump seeks a 'permanent' Iran deal (Al Jazeera)",
    "Bitcoin holds above $60,000 on Sunday (Finnhub)",
    "Gold holds near $5,355 (Reuters)",
    "UN talks on AI weapons end without rules (Wires)",
    "Pope Leo lunches with 1,300 poor guests (Vatican News)",
    "Ladakh: 70% turnout in first polls since 2019 (Daily World)",
]

UTC_ITEMS = [
    "01:00 HK polls open", "03:00 COP31 objections end", "05:11 Hamas seeks talks",
    "05:30 Verstappen wins Vegas", "06:00 COP31 approval due", "07:30 Approval slips",
    "08:00 161 of 186 downed", "14:00 HK turnout 93.55%",
]

REGIONS = [("EUROPE", 9, NAVY), ("ASIA-PACIFIC", 10, TEAL), ("MIDDLE EAST", 4, RED),
           ("AMERICAS", 5, (90, 60, 120)), ("AFRICA", 5, (34, 120, 60)),
           ("OCEANIA", 2, (200, 120, 30)), ("WORLD", 4, (90, 90, 88))]

STATS = [("~200", "nations at COP31"), ("03:00", "GMT objections close"),
         ("186", "drones fired"), ("161", "downed or jammed"),
         ("2", "US radars claimed hit"), ("856", "Hong Kong candidates")]

# lon/lat -> map box coords
MAP = (M, 744, 330, 128)


def map_xy(lon, lat):
    x0, y0, w, h = MAP
    return (int(x0 + (lon + 170) / 360.0 * w), int(y0 + (75 - lat) / 130.0 * h))


PINS = [(30.7, 36.9), (50.6, 26.2), (30.5, 50.5), (114.2, 22.3), (-115.1, 36.2),
        (174.8, -41.3), (26.0, 60.0), (51.4, 35.7), (-47.9, -15.8), (-77.0, 38.9),
        (4.35, 50.85), (93.9, 24.8), (34.5, 31.5)]


def draw_map(cv):
    x0, y0, w, h = MAP
    cv.rect(x0, y0, w, h, SEA)
    na = [(-168, 66), (-140, 70), (-120, 72), (-95, 80), (-80, 73), (-60, 60), (-55, 47),
          (-70, 42), (-75, 35), (-80, 26), (-90, 21), (-97, 16), (-105, 20), (-115, 30),
          (-125, 40), (-125, 49), (-140, 60), (-165, 60)]
    sa = [(-80, 10), (-70, 12), (-60, 8), (-50, 0), (-35, -8), (-40, -20), (-48, -28),
          (-58, -35), (-65, -45), (-70, -55), (-73, -40), (-72, -20), (-77, -12), (-80, -3)]
    eu = [(-10, 36), (-9, 43), (-2, 48), (0, 50), (5, 53), (8, 57), (10, 59), (18, 56),
          (21, 55), (24, 59), (28, 60), (30, 62), (28, 70), (20, 70), (12, 65), (5, 60),
          (-5, 58), (-10, 50), (-10, 43)]
    af = [(-17, 15), (-10, 30), (0, 36), (10, 37), (20, 32), (30, 31), (35, 28), (43, 12),
          (51, 11), (48, 0), (40, -10), (35, -20), (30, -30), (20, -35), (15, -30),
          (12, -18), (9, -5), (9, 4), (-8, 5), (-15, 12)]
    as_ = [(30, 36), (36, 36), (44, 39), (48, 30), (55, 26), (60, 25), (66, 25), (72, 20),
           (77, 8), (80, 7), (85, 20), (90, 22), (95, 16), (100, 8), (104, 2), (100, 10),
           (105, 20), (108, 12), (110, 20), (115, 23), (120, 30), (122, 38), (127, 40),
           (130, 42), (135, 44), (140, 45), (142, 50), (140, 60), (135, 65), (130, 70),
           (120, 73), (110, 74), (100, 76), (90, 75), (80, 73), (70, 72), (60, 70),
           (50, 68), (40, 68), (32, 70), (30, 66), (28, 60), (30, 55), (28, 50), (30, 45)]
    au = [(113, -22), (114, -30), (115, -35), (124, -33), (129, -32), (132, -32),
          (137, -35), (140, -38), (145, -38), (150, -37), (153, -27), (150, -22),
          (146, -19), (142, -11), (137, -12), (132, -12), (126, -14), (122, -17), (118, -20)]
    nz = [(167, -41), (174, -37), (178, -38), (175, -42), (170, -44)]
    for poly in (na, sa, eu, af, as_, au, nz):
        cv.poly([map_xy(lon, lat) for lon, lat in poly], LAND)
    OFF = {1: (-9, -7), 2: (10, 9), 3: (-8, 2), 7: (2, -12), 8: (11, -3),
           11: (-9, 3), 13: (1, 11)}
    for i, (lon, lat) in enumerate(PINS, 1):
        px, py = map_xy(lon, lat)
        dx, dy = OFF.get(i, (0, 0))
        px, py = px + dx, py + dy
        cv.circle(px, py, 6, RED)
        num = str(i)
        f = F("libsb9")
        f.draw(cv, px - f.width(num) // 2, py + 3, num, WHITE)


def render():
    cv = Canvas(W, H, PAPER)
    # ---- top bar
    F("libsb11").draw(cv, M, 20, "THE WORLD IN ONE DAY", RED)
    r = "39 STORIES · 7 REGIONS · EVERY ONE DATED SUNDAY 22 NOVEMBER 2026"
    F("libsb9").draw(cv, W - M - F("libsb9").width(r), 20, r, INK)
    cv.rect(M, 26, CW, 2, INK)
    # ---- masthead
    mast = "Sunday 22 November 2026"
    f = F("bodoni58")
    f.draw(cv, (W - f.width(mast)) // 2, 84, mast, INK)
    sub = "COP31 talks run into overtime · Iran claims strikes on US bases in Bahrain · Russia fires 186 drones at Ukraine"
    draw_lines(cv, M, 108, [sub], F("gelasio13"), INK, 16, "center", CW)
    cv.rect(M, 116, CW, 3, INK)
    cv.rect(M, 121, CW, 1, INK)
    # ---- stat strip
    cw = CW // 6
    for i, (num, cap) in enumerate(STATS):
        x = M + i * cw
        fn = F("bodoni30")
        fn.draw(cv, x + (cw - fn.width(num)) // 2, 152, num, RED if i in (2, 3) else NAVY)
        draw_lines(cv, x, 164, wrap(cap, F("libs9"), cw - 8), F("libs9"), GREY, 11, "center", cw)
        if i:
            cv.vline(x, 128, 44, LIGHT)
    cv.rect(M, 180, CW, 1, INK)
    # ---- region bar
    segs = [int(round(CW * n / 39.0)) for _, n, _ in REGIONS]
    segs[5] = max(segs[5], 58)
    segs[1] -= segs[5] - int(round(CW * 2 / 39.0))
    x = M
    for (name, n, col), seg in zip(REGIONS, segs):
        cv.rect(x, 184, seg, 20, col)
        lab = "%s %d" % (name, n)
        F("libsb9").draw(cv, x + (seg - F("libsb9").width(lab)) // 2, 198, lab, WHITE)
        x += seg
    # ---- UTC strip
    cv.rect(M, 210, CW, 28, (232, 226, 212))
    cv.rect(M, 210, 118, 28, RED)
    F("libsb9").draw(cv, M + 8, 227, "THE DAY IN UTC", WHITE)
    utc = "  ·  ".join(UTC_ITEMS)
    lines = wrap(utc, F("libs9"), CW - 128)
    draw_lines(cv, M + 126, 222, lines[:1], F("libs9"), INK, 11)
    if len(lines) > 1:
        draw_lines(cv, M + 126, 233, lines[1:2], F("libs9"), INK, 11)
    cv.rect(M, 240, CW, 1, INK)
    # ---- heroes
    hw, gap = 324, 12
    for i, hero in enumerate(HEROES):
        x = M + i * (hw + gap)
        y = 246
        hero["illo"](cv, x, y, hw, 92)
        cv.rect(x, y + 92, hw, 24, RED if i != 1 else NAVY)
        F("libsb11").draw(cv, x + 8, y + 92 + 17, hero["banner"], WHITE)
        bw = F("libsb9").width(hero["badge"]) + 12
        cv.rect(x + hw - bw - 6, y + 92 + 5, bw, 14, hero["badge_bg"])
        F("libsb9").draw(cv, x + hw - bw, y + 92 + 16, hero["badge"], hero["badge_fg"])
        F("libs9").draw(cv, x, y + 128, hero["kicker"], RED)
        draw_wrapped(cv, x, y + 148, hero["headline"], F("bask17"), INK, 21, hw, 2)
        draw_wrapped(cv, x, y + 148 + 42, hero["deck"], F("gelasio11"), INK, 13, hw, 4)
        F("roboto9").draw(cv, x, y + 148 + 42 + 52, hero["source"], GREY)
    # ---- secondary, two rows of five
    sw, sgap = 191, 10
    for row in range(2):
        for col in range(5):
            s = SECONDARY[row * 5 + col]
            x = M + col * (sw + sgap)
            y = 494 + row * 118
            cv.rect(x, y, sw, 16, s[1])
            lab = s[0]
            f = F("libsb9")
            if f.width(lab) > sw - 8:
                lab = lab.replace(" · ", " ")
            f.draw(cv, x + 5, y + 12, lab, WHITE)
            illo_small(cv, x, y + 16, sw, 28, s[2])
            draw_wrapped(cv, x, y + 58, s[3], F("bask13"), INK, 16, sw, 2)
            draw_wrapped(cv, x, y + 58 + 32, s[4], F("gelasio11"), INK, 13, sw, 2)
            F("roboto9").draw(cv, x, y + 58 + 32 + 24, s[5], GREY)
    # ---- map + also list
    F("libsb11").draw(cv, M, 738, "WHERE IT HAPPENED", INK)
    cv.rect(M, 742, 330, 1, INK)
    draw_map(cv)
    draw_lines(cv, M, 884, ["Pins 1–13 mark the pictured stories.", "Map: schematic, not to scale."],
               F("libs9"), GREY, 11)
    lx = M + 342
    F("libsb11").draw(cv, lx, 738, "ALSO ON SUNDAY 22 NOVEMBER — 26 MORE STORIES", INK)
    cv.rect(lx, 742, W - M - lx, 1, INK)
    colw = (W - M - lx - 12) // 2
    for i, item in enumerate(ALSO):
        col = i // 13
        row = i % 13
        x = lx + col * (colw + 12)
        y = 756 + row * 11
        num = "%d " % (i + 14)
        F("libsb10").draw(cv, x, y, num, RED)
        F("libs9").draw(cv, x + F("libsb10").width(num), y, item, INK)
    # ---- date check
    y = 906
    cv.rect(M, y, CW, 62, (250, 235, 235))
    cv.rect(M, y, CW, 1, RED)
    cv.rect(M, y + 61, CW, 1, RED)
    cv.rect(M, y, 1, 62, RED)
    cv.rect(M + CW - 1, y, 1, 62, RED)
    dc = ("DATE CHECK — Left out on purpose, they are NOT 22 November news: Russia's 400-drone barrage "
          "(19–20 Nov) · Peru quake (Fri 20 Nov) · Shenzhen summit (19 Nov) · BepiColombo Mercury burn "
          "(Sat 21 Nov) · 'El Chapo Isidro' captured (Fri 20 Nov) · EU–Indonesia signing (Sat 21 Nov) · "
          "Geneva killer-robot talks (ended Sat 21 Nov) · Gaza aid-van strike (Sat 21 Nov) · Kryvyi Rih "
          "strike (Fri night). Sparta II was struck Saturday — it stays ONLY because the ship was still "
          "burning at anchor off Finland on Sunday. Every story on this page happened, or was first "
          "reported, on Sunday 22 November 2026.")
    draw_wrapped(cv, M + 8, y + 14, dc, F("gelasio11"), INK, 14, CW - 16, 4)
    # ---- legend + footer
    leg = "ONGOING = still developing  ·  REPORTED = as reported, not yet confirmed  ·  CLAIM = one side's claim  ·  OFFICIALS SAY = official source"
    draw_lines(cv, M, 980, [leg], F("libs9"), GREY, 11, "center", CW)
    foot = "Sources named beside each story · Original flat-vector drawings, drawn in code · 39 stories · 7 regions"
    draw_lines(cv, M, 994, [foot], F("libs9"), GREY, 11, "center", CW)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    cv = render()
    write_png_rgb(os.path.join(out_dir, "entry.png"), W, H, bytes(cv.px))


if __name__ == "__main__":
    main()

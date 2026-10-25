"""Pixel-art street lamp, 24x68: plain, with a flyer, and broken.

The glass must stay at (14, 12, 8, 2): atmosphere.py repaints it while the lamp flickers.
Usage: python make_lamp.py <output dir>
"""
import sys
from PIL import Image

# Muted palette close to the street: dark greys, no near-black outline.
PAL = {
    '.': (0, 0, 0, 0),
    'o': (31, 32, 37, 255),     # soft outline / shadow side
    'd': (40, 41, 46, 255),     # metal dark
    'm': (52, 54, 60, 255),     # metal mid
    'l': (65, 67, 74, 255),     # metal light
    'h': (79, 81, 89, 255),     # metal highlight
    'r': (58, 44, 38, 255),     # rust dark
    'R': (80, 57, 43, 255),     # rust
    'Y': (98, 70, 50, 255),     # rust light
    'g': (218, 200, 147, 255),  # glass (repainted by the flicker)
    'G': (84, 78, 64, 255),     # dead glass
    'c': (40, 40, 42, 255),     # concrete dark
    'C': (52, 52, 53, 255),     # concrete mid
    'k': (63, 63, 63, 255),     # concrete light
    'K': (76, 76, 74, 255),     # concrete highlight
    'p': (116, 112, 99, 255),   # paper
    'P': (90, 87, 77, 255),     # paper shade
    't': (60, 58, 55, 255),     # print on paper
    'x': (0, 0, 0, 60),         # ground shadow
    'w': (28, 27, 29, 255),     # wire
}

HEAD = [
    "........................",  # 0
    "........................",
    "..........oo............",
    ".........ohmo...........",
    "..........hmo...........",
    "..........hmooooooo.....",  # 5
    "..........hmhhhllllmoo..",
    "..........hlllllllmmddo.",
    "..........hmmmmmmmmddddo",
    "..........hmdddddddddddo",
    "..........hmoRdddddrRddo",  # 10
    "..........hmoooooooooooo",
    "..........hmoogggggggggo"[:22] + "o.",
    "..........hmoogggggggggo"[:22] + "o.",
    "..........hmooooooooooo.",
]

POLE = [  # y15..39, 3 px wide at x10..12
    "..........hmo...........",  # 15
    "..........hmo...........",
    "..........hmo...........",
    "..........hRo...........",
    "..........hmo...........",
    ".........ohmdo..........",  # 20 band
    ".........odddo..........",
    "..........hmo...........",
    "..........hro...........",
    "..........lRo...........",
    "..........hmo...........",  # 25
    "..........hmo...........",
    "..........hmo...........",
    "..........hmo...........",
    "..........hmo...........",
    "..........hmo...........",  # 30
    "..........hmo...........",
    "..........hmo...........",
    "..........hRo...........",
    "..........hmo...........",
    "..........hmo...........",  # 35
    "..........hmo...........",
    "..........hRo...........",
    "..........hro...........",
    "..........hmo...........",
]

FLYER = {  # rows 28..34 replaced on the flyer variant
    28: ".........ppppP..........",
    29: ".........pttpP..........",
    30: ".........ppppP..........",
    31: ".........ptttP..........",
    32: ".........ppppP..........",
    33: ".........pPpPP..........",
    34: "..........Pmo...........",
}

LOWER = [  # y40..55, 4 px wide at x10..13
    ".........oooooo.........",  # 40 collar
    ".........ohhlmo.........",
    "..........hlmo..........",
    "..........hlmo..........",
    "..........hRmo..........",
    "..........hlmo..........",  # 45
    "..........hlmo..........",
    "..........hlro..........",
    "..........hlmo..........",
    "..........hlmo..........",
    "..........hlmo..........",  # 50
    "..........hRmo..........",
    "..........hlro..........",
    "..........hlmo..........",
    ".........ohlmdo.........",
    "........ohhlmddo........",  # 55
]

BASE = [  # y56..67
    ".....ooooooooooooo......",
    ".....oKKKKKkkkkkCo......",
    ".....okkkkkkkCCCco......",
    ".....ooooooooooooo......",
    ".....oCkkCCCCCCcco......",  # 60
    ".....oCkCCCCCcCcco......",
    ".....oCkCCrCCCCcco......",
    ".....oCkCCCCcCCcco......",
    ".....okCCCcCCCCcco......",
    ".....oCcccccccccco......",
    ".....ooooooooooooo......",
    "....xxxxxxxxxxxxxxx.....",
]


def build(rows):
    assert len(rows) == 68, len(rows)
    im = Image.new('RGBA', (24, 68))
    for y, row in enumerate(rows):
        assert len(row) == 24, (y, len(row), row)
        for x, ch in enumerate(row):
            im.putpixel((x, y), PAL[ch])
    return im


def put(rows, y, x, s):
    rows[y] = rows[y][:x] + s + rows[y][x + len(s):]


def broken(rows):
    rows = list(rows)
    put(rows, 6, 12, "hhoo")       # dented hood
    put(rows, 7, 13, "lRrl")
    put(rows, 8, 15, "RYRr")
    put(rows, 9, 17, "rRY")
    put(rows, 10, 13, "YRrRRrRY")
    for y in (12, 13):
        put(rows, y, 14, "G" * 8)  # dead glass
    for y, x in ((15, 21), (16, 21), (17, 22), (18, 22), (19, 21)):
        put(rows, y, x, "w")       # dangling wire
    put(rows, 46, 10, "Rlr")
    put(rows, 52, 10, "YRr")
    put(rows, 57, 5, ".o")         # chipped plinth corner
    put(rows, 58, 5, ".o")
    put(rows, 63, 11, "rr")
    return rows


rows = HEAD + POLE + LOWER + BASE
for y in (12, 13):
    assert rows[y][14:22] == "g" * 8, rows[y]
flyer = list(rows)
for y, row in FLYER.items():
    flyer[y] = row
out = sys.argv[1]
build(rows).save(out + '/lamp.png')
build(flyer).save(out + '/lamp_flyer.png')
build(broken(rows)).save(out + '/lamp_broken.png')
print('ok')

"""The readable note on the ground, 22x18 (data/items/note_ground.png).

A folded page torn from a notebook: ruled lines, red margin, handwriting, pinned by a pebble.
Drawn over the 16x12 pickup rect, offset by 3 px. Usage: python make_note.py <output png>
"""
import sys
from PIL import Image

PAL = {
    '.': (0, 0, 0, 0),
    'e': (100, 100, 94, 255),    # paper edge
    'W': (170, 169, 158, 255),   # paper, lit half
    'w': (152, 152, 143, 255),   # paper, far half
    'f': (126, 126, 119, 255),   # fold
    'b': (122, 132, 150, 255),   # ruled line
    'r': (146, 96, 90, 255),     # margin
    'i': (46, 50, 70, 255),      # ink
    'q': (46, 46, 48, 255),      # pebble shadow side
    'p': (68, 68, 70, 255),      # pebble
    'P': (94, 94, 96, 255),      # pebble lit
}

ROWS = [
    "......................",  # 0
    "...eeeeeeeeeeeeeeeee..",
    "..eWWrWWWWWfwwwwwwwe..",
    "...WWriiWiifwiiiwwwe..",
    "..ebbrbbbbbfbbbbbbbe..",
    "...WWrWiiiifiiwiiiwe..",  # 5
    "..eWWrWWWWWfwwwwwwwe..",
    "..ebbrbbbbbfbbbbbbbe..",
    "...WWriiiWifwiiiiwwe..",
    "..eWWrWWWWWfwwwwwwwe..",
    "..ebbrbbbbbfbbbbbbbe..",  # 10
    "...WWriiWiifwiwwqqqe..",
    "..eWWrWWWWWfwwwqPPpqq.",
    "..ebbrbbbbbfbbbqPpppq.",
    "...WWrWWWWWfwwwwqqqq..",
    "...eeeeeeeeeeeeeeeee..",  # 15
    "......................",
    "......................",
]

im = Image.new('RGBA', (22, 18))
for y, row in enumerate(ROWS):
    assert len(row) == 22, (y, len(row))
    for x, ch in enumerate(row):
        im.putpixel((x, y), PAL[ch])
shadow = (0, 0, 0, 70)
for y in range(17, -1, -1):
    for x in range(21, -1, -1):
        if im.getpixel((x, y))[3] == 255 and x + 1 < 22 and y + 1 < 18 and im.getpixel((x + 1, y + 1))[3] == 0:
            im.putpixel((x + 1, y + 1), shadow)
im.save(sys.argv[1])
print('ok')

"""Crumpled sheet lying on the asphalt, 32x24 (city_paper). The game lifts its top-right quarter in the wind.

Usage: python make_paper.py <output png>
"""
import random
import sys
from PIL import Image, ImageDraw

HI = (124, 119, 104, 255)    # paper facing the light
BA = (108, 104, 92, 255)     # paper
SD = (90, 87, 77, 255)       # shade / fold
DK = (72, 70, 64, 255)       # deep crease
PR = (78, 75, 68, 255)       # faded print
WT = (82, 78, 66, 255)       # damp stain
ED = (56, 55, 52, 255)       # soft edge
SH = (0, 0, 0, 55)           # shadow on the ground
rnd = random.Random(5)

im = Image.new('RGBA', (32, 24))
d = ImageDraw.Draw(im)
sheet = [(4, 4), (26, 2), (28, 18), (6, 21)]          # slightly turned sheet
d.polygon([(x + 1, y + 1) for x, y in sheet], fill=SH)
d.polygon(sheet, fill=BA, outline=ED)

# crumple: one vertical and one horizontal fold, light on one side, shade on the other
for y in range(3, 21):
    x = 15 + (y // 7)
    if im.getpixel((x, y)) == BA:
        im.putpixel((x, y), SD)
        if im.getpixel((x + 1, y)) == BA:
            im.putpixel((x + 1, y), HI)
for x in range(5, 28):
    y = 11 + (x // 9) - 1
    if im.getpixel((x, y)) in (BA, SD, HI):
        im.putpixel((x, y), SD)
        if im.getpixel((x, y - 1)) == BA:
            im.putpixel((x, y - 1), HI)

# faded handwriting / print lines, broken up
for row, (x0, x1) in zip((6, 8, 13, 15, 17), ((7, 13), (7, 12), (8, 13), (8, 12), (18, 24))):
    for x in range(x0, x1 + 1):
        if (x - x0) % 4 != 3 and im.getpixel((x, row)) in (BA, HI, SD):
            im.putpixel((x, row), PR)
for row, (x0, x1) in zip((5, 7, 9), ((18, 24), (18, 23), (19, 25))):
    for x in range(x0, x1 + 1):
        if (x - x0) % 5 != 4 and im.getpixel((x, row)) in (BA, HI, SD):
            im.putpixel((x, row), PR)

# damp stain soaking in from the lower edge
for x, y in ((8, 19), (9, 19), (10, 19), (9, 18), (10, 18), (11, 19), (12, 20), (7, 20), (8, 20), (9, 20), (10, 20), (11, 20)):
    if im.getpixel((x, y))[3] == 255 and im.getpixel((x, y)) != ED:
        im.putpixel((x, y), WT)

# folded-over bottom-right corner showing the back side
for x, y in ((25, 15), (26, 15), (26, 16), (25, 16), (24, 16), (27, 16), (26, 17), (25, 17), (27, 17)):
    im.putpixel((x, y), SD)
for x, y in ((24, 15), (24, 17), (28, 17), (27, 18)):
    im.putpixel((x, y), ED)
# torn nick on the top edge
im.putpixel((11, 3), (0, 0, 0, 0)); im.putpixel((12, 3), (0, 0, 0, 0)); im.putpixel((12, 4), ED)

im.save(sys.argv[1])
print('ok')

"""Bus stop, two 128x60 layers placed at the same spot: decor_008 (bench) and decor_009 (shelter).

Muted palette with soft edges, matching the lamps and the phone booth.
Usage: python make_stop.py <output dir>
"""
import random
import sys
from PIL import Image

E = (34, 35, 40, 255)       # soft edge
D = (42, 43, 48, 255)       # metal dark
M = (54, 56, 62, 255)       # metal mid
L = (64, 66, 73, 255)       # metal light
RU = (80, 57, 43, 255)      # rust
RD = (60, 46, 40, 255)      # rust dark
GL = (52, 62, 70, 120)      # glass
GR = (78, 88, 96, 120)      # reflection
GS = (66, 74, 80, 150)      # scratches / grime
P1, P2, P3 = (112, 102, 84, 255), (92, 84, 70, 255), (70, 62, 54, 255)   # faded poster
SG, SL = (150, 132, 78, 255), (52, 46, 36, 255)                           # stop plate and its letter
W1, W2, W3 = (62, 52, 44, 255), (76, 64, 52, 255), (88, 74, 60, 255)      # wood
SH = (0, 0, 0, 50)
rnd = random.Random(11)


def canvas():
    return Image.new('RGBA', (128, 60))


def rect(im, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            im.putpixel((x, y), c)


def shelter():
    im = canvas()
    # back glass between the posts, three panels
    rect(im, 8, 13, 119, 53, GL)
    for x0 in (8, 46, 84):
        for i in range(10):                 # two soft diagonal reflections per panel
            for x, y in ((x0 + 6 + i, 40 - i * 2), (x0 + 12 + i, 50 - i * 2)):
                if 13 < y < 53:
                    im.putpixel((x, y), GR)
                    im.putpixel((x, y + 1), GR)
    for _ in range(40):                      # grime along the bottom
        x, y = rnd.randint(8, 119), rnd.randint(46, 53)
        im.putpixel((x, y), GS)
    for x, y in ((60, 30), (61, 31), (62, 31), (63, 32), (61, 29), (59, 31), (64, 33)):
        im.putpixel((x, y), GS)              # crack
    # panel frames
    for x in (45, 83):
        rect(im, x, 13, x, 53, M)
    rect(im, 8, 53, 119, 54, D)              # bottom rail
    rect(im, 8, 54, 119, 54, E)
    # faded poster on the right panel, one corner torn
    rect(im, 96, 20, 113, 43, P2)
    rect(im, 97, 21, 112, 42, P1)
    rect(im, 99, 24, 110, 32, P3)            # photo
    rect(im, 103, 26, 106, 29, P2)
    for y in (35, 37, 39):
        rect(im, 99, y, 108 if y != 39 else 104, y, P3)
    rect(im, 110, 39, 113, 43, GL)           # torn corner
    im.putpixel((109, 41), P2); im.putpixel((110, 38), P2)
    # roof: underside, slab, front edge
    rect(im, 0, 0, 127, 1, E)
    rect(im, 1, 1, 126, 5, M)
    rect(im, 1, 1, 126, 1, L)
    rect(im, 0, 6, 127, 7, D)
    rect(im, 0, 8, 127, 8, E)
    rect(im, 8, 9, 119, 12, (36, 37, 42, 255))   # header under the roof
    for _ in range(18):
        x, y = rnd.randint(2, 125), rnd.randint(2, 7)
        im.putpixel((x, y), RU if rnd.random() < .5 else RD)
    for x in (20, 21, 70, 104):
        im.putpixel((x, 8), RU); im.putpixel((x, 9), RD)   # rust drips
    # stop plate on the front edge
    rect(im, 12, 2, 21, 7, E)
    rect(im, 13, 3, 20, 6, SG)
    for x, y in ((16, 3), (17, 3), (15, 4), (18, 4), (15, 5), (16, 5), (17, 5), (18, 5), (15, 6), (18, 6)):
        im.putpixel((x, y), SL)               # "А"
    # posts
    for x0 in (5, 120):
        rect(im, x0, 8, x0 + 2, 55, M)
        rect(im, x0, 8, x0, 55, L)
        rect(im, x0 + 2, 8, x0 + 2, 55, E)
        rect(im, x0 - 1, 55, x0 + 3, 57, D)  # foot plate
        rect(im, x0 - 1, 57, x0 + 3, 57, E)
        for y in (30, 31, 44):
            im.putpixel((x0 + 1, y), RU)
    rect(im, 3, 58, 124, 58, SH)
    return im


def bench():
    im = canvas()
    # backrest: two slats
    for y in (31, 35):
        rect(im, 16, y, 76, y + 2, W2)
        rect(im, 16, y, 76, y, W3)
        rect(im, 16, y + 2, 76, y + 2, W1)
    # seat
    rect(im, 15, 39, 77, 42, W2)
    rect(im, 15, 39, 77, 39, W3)
    rect(im, 15, 42, 77, 42, W1)
    rect(im, 15, 43, 77, 43, E)
    # one broken backrest slat end and wear
    rect(im, 68, 35, 76, 37, (0, 0, 0, 0))
    im.putpixel((67, 36), W1); im.putpixel((67, 37), W1)
    for _ in range(30):
        x, y = rnd.randint(16, 76), rnd.randint(31, 42)
        if im.getpixel((x, y))[3]:
            im.putpixel((x, y), W1)
    # frame: back posts and legs
    for x in (19, 72):
        rect(im, x, 30, x + 1, 49, D)
        rect(im, x, 30, x, 49, M)
        im.putpixel((x, 46), RU)
    rect(im, 17, 49, 23, 49, E)
    rect(im, 70, 49, 76, 49, E)
    rect(im, 15, 50, 78, 50, SH)
    return im


out = sys.argv[1]
bench().save(out + '/decor_008.png')
shelter().save(out + '/decor_009.png')
print('ok')

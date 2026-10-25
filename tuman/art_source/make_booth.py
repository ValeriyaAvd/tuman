"""Pixel-art phone booth, 28x56 (decor_007). Lit sign near (14, 2) where the map's booth glow sits.

Muted palette to match the street and the lamps. Usage: python make_booth.py <output png>
"""
import random
import sys
from PIL import Image

O = (60, 31, 31, 255)       # edge: just a shade under the red shadow
R1 = (66, 32, 32, 255)      # red shadow
R2 = (88, 40, 38, 255)      # red mid
R3 = (108, 52, 46, 255)     # red light
R4 = (126, 66, 58, 255)     # red highlight
RU = (80, 57, 43, 255)      # rust
RD = (58, 44, 38, 255)      # rust dark
G1 = (30, 36, 42, 255)      # interior
G2 = (40, 48, 56, 255)      # glass
G3 = (58, 68, 76, 255)      # reflection
G4 = (76, 86, 92, 255)      # reflection highlight
SL = (196, 180, 132, 255)   # lit sign
SD = (96, 78, 58, 255)      # sign letters
BK = (26, 26, 29, 255)      # phone body / cord
PH = (66, 67, 72, 255)      # phone metal
C1, C2, C3, C4 = (40, 40, 42, 255), (52, 52, 53, 255), (63, 63, 63, 255), (76, 76, 74, 255)
SH = (0, 0, 0, 60)

im = Image.new('RGBA', (28, 56))
rnd = random.Random(7)


def rect(x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            im.putpixel((x, y), c)


def px(x, y, c):
    im.putpixel((x, y), c)


# --- roof and sign ---------------------------------------------------------
rect(2, 0, 25, 1, O)
rect(3, 1, 24, 1, R1)
rect(1, 2, 26, 6, O)
rect(2, 2, 25, 5, R2)
rect(6, 2, 21, 4, SL)                     # lit "ТЕЛЕФОН" plate
for x in (7, 8, 10, 12, 13, 15, 17, 18, 20):
    px(x, 3, SD)
px(6, 4, (168, 152, 110, 255)); px(21, 4, (168, 152, 110, 255))
rect(0, 6, 27, 7, O)                      # overhang
rect(1, 6, 26, 6, R1)
px(3, 6, R2); px(11, 6, RU); px(19, 6, R2)

# --- body frame --------------------------------------------------------------
rect(2, 8, 25, 50, O)
rect(3, 8, 24, 49, R2)
rect(24, 8, 24, 49, R1)                   # shaded right edge
rect(23, 8, 23, 49, R1)

# --- glazed door: 2 columns x 4 rows of panes --------------------------------
panes_x = [(6, 12), (14, 20)]
panes_y = [(10, 16), (18, 24), (26, 32), (34, 40)]
for x0, x1 in panes_x:
    for y0, y1 in panes_y:
        rect(x0, y0, x1, y1, G2)
        rect(x0, y0, x1, y0, G1)          # inner shadow on top of each pane
        rect(x0, y0, x0, y1, R1)
# dim interior seen through the glass
rect(7, 11, 12, 40, G1)
rect(15, 11, 20, 40, G1)
for x0, x1 in panes_x:
    for y0, y1 in panes_y:
        rect(x0, y0, x1, y0, G1)
# phone on the back wall (left column) and the receiver hanging on its cord
rect(8, 19, 11, 24, BK)
rect(9, 20, 10, 21, PH)
px(9, 23, PH)
for y in range(25, 34):
    px(10 if y % 3 else 11, y, BK)        # cord
rect(9, 34, 11, 35, BK)                   # dangling receiver
px(10, 35, PH)
px(11, 27, G1); px(10, 30, BK)
# glass reflections: short diagonal streaks
for x0, y0 in ((6, 16), (14, 15), (6, 32), (14, 31), (17, 24)):
    for i in range(3):
        if 0 <= x0 + i < 28:
            px(x0 + i, y0 - i, G3)
    px(x0, y0, G4)
# a cracked pane on the right
for x, y in ((18, 34), (17, 35), (18, 36), (19, 37), (16, 36), (19, 35)):
    px(x, y, G4)

# mullions (already R2 between panes); highlight their left side
for y in range(10, 41):
    px(13, y, R2)
for y0, y1 in panes_y:
    rect(6, y1 + 1, 20, y1 + 1, R2)

# door handle
rect(22, 24, 22, 29, (42, 42, 46, 255))
px(22, 24, PH); px(22, 25, PH)

# --- kick panel ------------------------------------------------------------
rect(5, 42, 21, 48, R1)
rect(5, 42, 21, 42, O)
rect(6, 43, 20, 47, R2)
for x in (7, 19):
    px(x, 45, R1)                          # rivets

# wear: chipped paint and rust streaks
for _ in range(22):
    x, y = rnd.randint(3, 24), rnd.randint(8, 49)
    if im.getpixel((x, y)) in (R2, R3, R4, R1):
        px(x, y, RU if rnd.random() < .6 else RD)
for x in (8, 17):
    for y in range(48, 50):
        px(x, y, RU)
px(5, 9, RD); px(24, 30, RD); px(24, 31, RU)

# --- concrete step -----------------------------------------------------------
rect(1, 50, 26, 53, C1)
rect(2, 50, 25, 50, C3)
rect(2, 51, 25, 52, C2)
rect(2, 51, 4, 52, C2)
px(12, 52, C1); px(20, 51, C1); px(21, 52, RD)
rect(0, 54, 27, 54, SH)
rect(1, 55, 26, 55, (0, 0, 0, 30))

im.save(sys.argv[1])
print('ok')

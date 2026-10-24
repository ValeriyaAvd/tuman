# =====================================================
#  world.py — мир игры: карта, земля, дома, машины, деревья, фонари,
#  туман, свет и луч фонарика.
#  Сама карта лежит в файле data/map.txt.
# =====================================================

import os
import math
import random
import pygame
from settings import *

# Через какие клетки нельзя пройти (буквы — как в data/map.txt)
SOLID = "#TbHKBFXLlCcAWSRQDG"

# Из каких букв какая "земля" под ними
GRASS_TILES = ",Tb#H"
SIDEWALK_TILES = "_KBFXLlN"
ROAD_TILES = ".=O~CcP"


def fence_is_horizontal(rows, x, y):
    """Забор в этой клетке идёт только слева направо (не столбиком и не угол)?
    За краем карты считаем, что тоже забор — так края карты остаются сплошными."""
    def is_fence(xx, yy):
        if 0 <= yy < len(rows) and 0 <= xx < len(rows[0]):
            return rows[yy][xx] == "#"
        return True
    return not is_fence(x, y - 1) and not is_fence(x, y + 1)


# ---------- ЗАГРУЗКА КАРТЫ ----------
def read_map_file(file_name):
    """Читает карту из файла в папке data. Строки, которые начинаются с //, пропускаем."""
    path = os.path.join(DATA_DIR, file_name)
    with open(path, encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in f]
    return [line for line in lines if line and not line.startswith("//")]


def load_map(file_name="map.txt"):
    """Читает карту и находит стены, старт героя, записку и монстров."""
    rows = read_map_file(file_name)
    width = max(len(row) for row in rows)
    rows = [row.ljust(width, "#") for row in rows]  # выравниваем строки по длине

    walls = []
    player_start = (TILE, TILE)
    note_rect = None
    monster_starts = []

    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            rect = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
            if ch in "Ll":
                # У фонаря мешает пройти только основание столба, а не вся клетка —
                # поэтому за фонарём можно пройти по тротуару
                walls.append(pygame.Rect(rect.centerx - 3, rect.bottom - 4, 6, 4))
            elif ch == "T":
                # У дерева мешает пройти только ствол — под листвой пройти можно
                walls.append(pygame.Rect(rect.centerx - 3, rect.bottom - 4, 6, 4))
            elif ch == "b":
                # У куста мешает пройти только его низ — за верхушкой встать можно
                walls.append(pygame.Rect(rect.x + 3, rect.bottom - 5, 10, 4))
            elif ch == "B":
                pass                                       # остановку обрабатываем ниже, целиком
            elif ch == "#" and fence_is_horizontal(rows, x, y):
                # Через забор не пройти, но можно подойти к нему вплотную и сзади, и спереди
                walls.append(pygame.Rect(rect.x, rect.bottom - 5, TILE, 4))
            elif ch in SOLID:
                walls.append(rect)
            if ch == "P":
                player_start = (rect.x + 4, rect.y + 8)
            if ch == "N":
                note_rect = pygame.Rect(rect.x + 4, rect.y + 5, 8, 6)
            if ch == "M":
                monster_starts.append((rect.x + 4, rect.y + 8))

    # Остановка смотрит на дорогу: с тротуара (сверху) можно зайти под крышу
    # и подойти к скамейке, а сзади (со стороны парка) не пускает стекло
    for r in find_groups(rows, "B"):
        walls.append(pygame.Rect(r.x + 2, r.y + 2, 2, 14))                 # левая стойка
        walls.append(pygame.Rect(r.right - 4, r.y + 2, 2, 14))             # правая стойка
        walls.append(pygame.Rect(r.x + 8, r.y + 7, r.w - 34, 4))           # скамейка
        walls.append(pygame.Rect(r.x, r.y + 11, r.w, 4))                   # заднее стекло

    return rows, walls, player_start, note_rect, monster_starts


def find_groups(rows, letter):
    """Находит группы соседних клеток с одной буквой (например, все H одного дома)
    и возвращает для каждой группы прямоугольник в пикселях."""
    seen = set()
    groups = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != letter or (x, y) in seen:
                continue
            # "Заливка": от найденной клетки обходим всех соседей с той же буквой
            stack = [(x, y)]
            seen.add((x, y))
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= ny < len(rows) and 0 <= nx < len(rows[0]) \
                            and rows[ny][nx] == letter and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            groups.append(pygame.Rect(min(xs) * TILE, min(ys) * TILE,
                                      (max(xs) - min(xs) + 1) * TILE,
                                      (max(ys) - min(ys) + 1) * TILE))
    return groups


# ---------- СВЕЧЕНИЕ (фонари, окна) ----------
def make_glow(radius, color):
    """Круглое мягкое пятно света. Его рисуют в режиме "сложения цветов",
    поэтому чёрный край ничего не меняет, а центр подсвечивает картинку."""
    glow = pygame.Surface((radius * 2, radius * 2))
    glow.fill((0, 0, 0))
    for r in range(radius, 0, -1):
        k = (1 - r / radius) ** 1.6          # чем ближе к центру, тем ярче
        c = tuple(int(v * k) for v in color)
        pygame.draw.circle(glow, c, (radius, radius), r)
    return glow


# ---------- РИСОВАНИЕ ЗЕМЛИ ----------
def speckle(surf, rect, color, count, rnd):
    """Рисует случайные точки — 'шум', чтобы клетка не была плоской."""
    for _ in range(count):
        px = rect.x + rnd.randrange(rect.w)
        py = rect.y + rnd.randrange(rect.h)
        surf.set_at((px, py), color)


def draw_crack(surf, r, rnd, color):
    """Трещина: ломаная линия из нескольких отрезков."""
    x = r.x + rnd.randrange(2, TILE - 2)
    y = r.y + rnd.randrange(2, TILE - 2)
    for _ in range(rnd.randint(2, 4)):
        nx = max(r.x, min(r.right - 1, x + rnd.randint(-5, 5)))
        ny = max(r.y, min(r.bottom - 1, y + rnd.randint(-5, 5)))
        pygame.draw.line(surf, color, (x, y), (nx, ny))
        x, y = nx, ny


def draw_leaves(surf, r, rnd):
    """Опавшие листья — пара рыжих точек."""
    for _ in range(rnd.randint(1, 3)):
        c = rnd.choice([(104, 66, 38), (88, 56, 34), (112, 84, 44)])
        x = r.x + rnd.randrange(TILE - 1)
        y = r.y + rnd.randrange(TILE - 1)
        surf.fill(c, (x, y, 2, 1))


def draw_ground(surf, rows, rnd):
    h = len(rows)
    w = len(rows[0])

    def at(x, y):
        if 0 <= x < w and 0 <= y < h:
            return rows[y][x]
        return "#"

    def ground(x, y):
        """Какая земля под клеткой. У предметов (фонарь, бак, лужа...) земля
        берётся от соседей: фонарь на траве стоит на траве, на асфальте — на асфальте."""
        ch = at(x, y)
        if ch in ",._A:":
            return ch
        if ch in "#TbH":
            return ","
        if ch in "WDG":
            return "W"
        counts = {}
        for n in (at(x - 1, y), at(x + 1, y), at(x, y - 1), at(x, y + 1)):
            g = "," if n in GRASS_TILES else "_" if n in "_K" else "." if n in ".=O" else ":" if n in ":SRQ*" else None
            if g:
                counts[g] = counts.get(g, 0) + 1
        if not counts:
            return "_" if ch in SIDEWALK_TILES else "."
        return max(counts, key=counts.get)

    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            r = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
            base = ground(x, y)

            if base == ",":                                        # трава
                surf.fill((40, 50, 40), r)
                speckle(surf, r, (52, 64, 48), 10, rnd)
                speckle(surf, r, (30, 38, 31), 8, rnd)
                if rnd.random() < 0.3:                             # сухие травинки
                    tx, ty = r.x + rnd.randrange(14), r.y + rnd.randrange(12)
                    pygame.draw.line(surf, (70, 72, 52), (tx, ty + 3), (tx + 1, ty))
                if rnd.random() < 0.25:
                    draw_leaves(surf, r, rnd)

            elif base == "_":                                     # тротуарная плитка
                surf.fill((84, 84, 88), r)
                speckle(surf, r, (94, 94, 98), 6, rnd)
                speckle(surf, r, (72, 72, 76), 6, rnd)
                shift = 4 if y % 2 else 0                          # плитка уложена "кирпичиком"
                pygame.draw.line(surf, (68, 68, 72), (r.x, r.y), (r.right - 1, r.y))
                pygame.draw.line(surf, (68, 68, 72), (r.x, r.y + 8), (r.right - 1, r.y + 8))
                for sx in (r.x + shift, r.x + shift + 8):
                    pygame.draw.line(surf, (68, 68, 72), (sx, r.y), (sx, r.y + 7))
                    pygame.draw.line(surf, (68, 68, 72), (sx + 4 - shift, r.y + 8), (sx + 4 - shift, r.bottom - 1))
                if rnd.random() < 0.1:
                    draw_crack(surf, r, rnd, (56, 56, 60))
                if rnd.random() < 0.2:
                    draw_leaves(surf, r, rnd)

            elif base == ".":                                     # асфальт
                surf.fill((58, 58, 62), r)
                speckle(surf, r, (68, 68, 72), 8, rnd)
                speckle(surf, r, (48, 48, 52), 8, rnd)
                if rnd.random() < 0.15:
                    draw_crack(surf, r, rnd, (40, 40, 44))

            elif base == ":":                                     # пол в помещении (линолеум)
                light = (x + y) % 2 == 0                           # клетки через одну — как шахматка
                surf.fill((70, 66, 58) if light else (58, 55, 49), r)
                speckle(surf, r, (48, 45, 40), 6, rnd)
                if rnd.random() < 0.15:
                    draw_crack(surf, r, rnd, (44, 42, 38))         # потёртости

            elif base == "W":                                     # стена
                if ground(x, y + 1) == ":":                        # снизу пол — видна сама стена с обоями
                    surf.fill((86, 92, 84), r)
                    for i in range(r.x + 2, r.right, 4):
                        pygame.draw.line(surf, (76, 82, 74), (i, r.y), (i, r.bottom - 4))   # полоски обоев
                    surf.fill((52, 44, 38), (r.x, r.bottom - 3, TILE, 3))                  # плинтус
                    if rnd.random() < 0.3:                                                # пятна сырости
                        pygame.draw.ellipse(surf, (70, 76, 68), (r.x + rnd.randrange(8), r.y + rnd.randrange(8), 6, 5))
                else:                                              # иначе видна только тёмная "крышка" стены
                    surf.fill((16, 15, 17), r)

            else:                                                  # пропасть
                surf.fill((8, 8, 10), r)
                speckle(surf, r, (16, 16, 19), 4, rnd)

            # --- детали поверх земли ---
            if ch == "=":                                          # разметка (стёртая)
                for i in range(TILE):
                    if rnd.random() < 0.85:
                        surf.fill((150, 146, 128), (r.x + i, r.centery - 1, 1, 2))

            if ch == "~":                                          # лужа
                pygame.draw.ellipse(surf, (34, 38, 46), (r.x + 1, r.y + 4, 14, 8))
                pygame.draw.ellipse(surf, (34, 38, 46), (r.x + 5, r.y + 2, 8, 6))
                pygame.draw.line(surf, (74, 82, 96), (r.x + 4, r.y + 6), (r.x + 9, r.y + 6))
                surf.set_at((r.x + 11, r.y + 8), (74, 82, 96))

            if ch == "O":                                          # люк
                pygame.draw.circle(surf, (36, 36, 40), r.center, 7)
                pygame.draw.circle(surf, (50, 50, 54), r.center, 6)
                for i in range(-3, 4, 2):
                    pygame.draw.line(surf, (40, 40, 44), (r.centerx - 4, r.centery + i), (r.centerx + 3, r.centery + i))

            if base == "_":                                       # бордюр у дороги
                if at(x, y + 1) in ROAD_TILES:
                    surf.fill((118, 118, 122), (r.x, r.bottom - 2, TILE, 2))
                if at(x, y - 1) in ROAD_TILES:
                    surf.fill((118, 118, 122), (r.x, r.y, TILE, 2))
                if at(x + 1, y) in ROAD_TILES:
                    surf.fill((118, 118, 122), (r.right - 2, r.y, 2, TILE))
                if at(x - 1, y) in ROAD_TILES:
                    surf.fill((118, 118, 122), (r.x, r.y, 2, TILE))

            if ch == "A":                                          # рваный край обрыва
                for nx, ny, side in ((x, y - 1, "top"), (x, y + 1, "bottom"), (x - 1, y, "left"), (x + 1, y, "right")):
                    if at(nx, ny) == "A" or at(nx, ny) == "#":
                        continue
                    for i in range(TILE):
                        depth = rnd.randint(1, 4)
                        if side == "top":
                            surf.fill((44, 44, 48), (r.x + i, r.y, 1, depth))
                        elif side == "bottom":
                            surf.fill((44, 44, 48), (r.x + i, r.bottom - depth, 1, depth))
                        elif side == "left":
                            surf.fill((44, 44, 48), (r.x, r.y + i, depth, 1))
                        else:
                            surf.fill((44, 44, 48), (r.right - depth, r.y + i, depth, 1))
                speckle(surf, r, (30, 30, 33), 3, rnd)             # обломки

            if ch == "#" and fence_is_horizontal(rows, x, y):
                surf.fill((30, 38, 31), (r.x, r.bottom - 2, TILE, 2))   # только тень: сам забор рисуется отдельно
            elif ch == "#":                                        # сетчатый забор (столбиком и углы)
                horiz = at(x - 1, y) == "#" or at(x + 1, y) == "#"
                vert = at(x, y - 1) == "#" or at(x, y + 1) == "#"
                if horiz or not vert:
                    surf.fill((30, 38, 31), (r.x, r.bottom - 2, TILE, 2))           # тень
                    for i in range(0, TILE, 3):                                     # сетка
                        pygame.draw.line(surf, (82, 84, 90), (r.x + i, r.y + 4), (r.x + i + 3, r.bottom - 3))
                        pygame.draw.line(surf, (70, 72, 78), (r.x + i + 3, r.y + 4), (r.x + i, r.bottom - 3))
                    pygame.draw.line(surf, (112, 112, 118), (r.x, r.y + 4), (r.right - 1, r.y + 4))
                    pygame.draw.line(surf, (96, 96, 102), (r.x, r.bottom - 3), (r.right - 1, r.bottom - 3))
                    surf.fill((44, 42, 44), (r.x, r.y + 3, 2, 11))                  # столбик
                if vert:
                    for i in range(0, TILE, 3):
                        pygame.draw.line(surf, (82, 84, 90), (r.x + 4, r.y + i), (r.x + 11, r.y + i + 3))
                    pygame.draw.line(surf, (112, 112, 118), (r.x + 4, r.y), (r.x + 4, r.bottom - 1))
                    pygame.draw.line(surf, (96, 96, 102), (r.x + 11, r.y), (r.x + 11, r.bottom - 1))


def make_fence():
    """Одна клетка сетчатого забора — отдельная картинка, чтобы за забором можно было стоять."""
    img = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    for i in range(0, TILE, 3):                                       # сетка
        pygame.draw.line(img, (82, 84, 90), (i, 4), (i + 3, TILE - 3))
        pygame.draw.line(img, (70, 72, 78), (i + 3, 4), (i, TILE - 3))
    pygame.draw.line(img, (112, 112, 118), (0, 4), (TILE - 1, 4))       # верхняя перекладина
    pygame.draw.line(img, (96, 96, 102), (0, TILE - 3), (TILE - 1, TILE - 3))   # нижняя
    img.fill((44, 42, 44), (0, 3, 2, 11))                             # столбик
    return img


# ---------- ПОСТРОЙКИ И МАШИНЫ ----------
def shade(color, k):
    """Делает цвет темнее (k < 1) или светлее (k > 1)."""
    return tuple(max(0, min(255, int(v * k))) for v in color)


def draw_house(surf, rect, rnd, glows):
    """Дом в виде сверху-спереди: сверху крыша, снизу полоска стены с окнами и дверью."""
    roof = rnd.choice([(84, 50, 44), (62, 60, 70), (74, 64, 50), (54, 66, 62)])
    wall_color = rnd.choice([(124, 116, 104), (110, 112, 108), (128, 110, 96)])
    facade_h = 14

    surf.fill((24, 28, 25), rect.move(3, 3))                               # тень от дома

    roof_rect = pygame.Rect(rect.x, rect.y, rect.w, rect.h - facade_h)
    mid = roof_rect.y + roof_rect.h // 2
    surf.fill(shade(roof, 1.25), (roof_rect.x, roof_rect.y, roof_rect.w, mid - roof_rect.y))  # освещённый скат
    surf.fill(roof, (roof_rect.x, mid, roof_rect.w, roof_rect.bottom - mid))                 # теневой скат
    for i, yy in enumerate(range(roof_rect.y + 3, roof_rect.bottom, 4)):   # черепица
        pygame.draw.line(surf, shade(roof, 0.8), (roof_rect.x, yy), (roof_rect.right - 1, yy))
        for xx in range(roof_rect.x + (3 if i % 2 else 0), roof_rect.right, 6):
            surf.fill(shade(roof, 0.8), (xx, yy - 3, 1, 3))
    pygame.draw.line(surf, shade(roof, 1.5), (roof_rect.x, mid), (roof_rect.right - 1, mid))   # конёк
    pygame.draw.rect(surf, shade(roof, 0.55), roof_rect, 1)
    for _ in range(rnd.randint(2, 5)):                                    # мох и пятна
        surf.fill(shade(roof, 0.7), (rnd.randrange(roof_rect.x + 2, roof_rect.right - 4),
                                     rnd.randrange(roof_rect.y + 2, roof_rect.bottom - 3), 3, 2))
    chim = pygame.Rect(rnd.randrange(rect.x + 6, rect.right - 14), roof_rect.y + 3, 6, 8)   # труба
    surf.fill((92, 54, 44), chim)
    surf.fill((40, 30, 28), (chim.x + 1, chim.y + 1, 4, 2))

    wall = pygame.Rect(rect.x + 1, roof_rect.bottom, rect.w - 2, facade_h)
    surf.fill(wall_color, wall)
    surf.fill(shade(wall_color, 0.85), (wall.x, wall.y, wall.w, 2))       # тень под крышей
    surf.fill(shade(wall_color, 0.6), (wall.x, wall.bottom - 2, wall.w, 2))  # цоколь

    door = pygame.Rect(rect.centerx - 4, wall.bottom - 11, 8, 11)
    for wx in range(rect.x + 5, rect.right - 9, 14):
        if abs(wx + 3 - rect.centerx) < 10:
            continue
        win = pygame.Rect(wx, wall.y + 3, 7, 6)
        surf.fill(shade(wall_color, 0.5), win.inflate(2, 2))              # рама
        if rnd.random() < 0.15:
            surf.fill((150, 118, 66), win)                                # где-то горит свет...
            glows.append(("window", win.centerx, win.centery))
        else:
            surf.fill((22, 26, 32), win)
            surf.set_at((win.x + 1, win.y + 1), (60, 68, 80))             # блик на стекле
        pygame.draw.line(surf, shade(wall_color, 0.5), (win.centerx, win.y), (win.centerx, win.bottom - 1))
        if rnd.random() < 0.2:                                            # заколоченное окно
            pygame.draw.line(surf, (100, 78, 56), (win.x - 1, win.y + 1), (win.right, win.bottom - 2), 2)
    surf.fill((58, 40, 32), door)
    surf.fill((44, 30, 24), (door.x, door.y, door.w, 1))
    surf.set_at((door.right - 2, door.centery + 1), (170, 150, 90))      # ручка
    surf.fill((96, 96, 100), (door.x - 2, door.bottom, door.w + 4, 2))    # ступенька


def draw_shop(surf, rect, rnd, glows):
    """Магазин: плоская крыша, витрины, полосатый навес."""
    facade_h = 18
    surf.fill((24, 28, 25), rect.move(3, 3))

    roof = pygame.Rect(rect.x, rect.y, rect.w, rect.h - facade_h)
    surf.fill((74, 74, 78), roof)
    speckle(surf, roof, (66, 66, 70), 60, rnd)
    pygame.draw.rect(surf, (52, 52, 56), roof, 3)                         # бортик крыши
    for _ in range(3):                                                    # вентиляция
        v = pygame.Rect(rnd.randrange(roof.x + 8, roof.right - 18), rnd.randrange(roof.y + 6, roof.bottom - 16), 10, 8)
        surf.fill((30, 30, 32), v.move(1, 2))
        surf.fill((100, 100, 104), v)
        for i in range(v.x + 2, v.right - 1, 2):
            pygame.draw.line(surf, (70, 70, 74), (i, v.y + 2), (i, v.bottom - 3))
    for _ in range(4):                                                    # тёмные пятна от воды
        pygame.draw.ellipse(surf, (64, 64, 68), (rnd.randrange(roof.x + 4, roof.right - 20),
                                                 rnd.randrange(roof.y + 4, roof.bottom - 12), 16, 8))

    wall = pygame.Rect(rect.x + 1, roof.bottom, rect.w - 2, facade_h)
    surf.fill((108, 102, 94), wall)
    sign = pygame.Rect(rect.centerx - 28, wall.y, 56, 5)                  # вывеска
    surf.fill((40, 36, 34), sign)
    for i in range(sign.x + 3, sign.right - 3, 4):
        if rnd.random() < 0.7:
            surf.fill((120, 104, 60), (i, sign.y + 1, 3, 3))              # выцветшие буквы
    for i, sx in enumerate(range(wall.x, wall.right, 4)):                 # полосатый навес
        surf.fill((116, 40, 40) if i % 2 == 0 else (150, 142, 132), (sx, wall.y + 5, 4, 3))
    surf.fill((60, 30, 30), (wall.x, wall.y + 8, wall.w, 1))

    door = pygame.Rect(rect.centerx - 8, wall.y + 9, 16, 9)
    for wx in range(wall.x + 4, wall.right - 20, 22):                     # витрины
        if wx < door.right + 2 and wx + 18 > door.x - 2:
            continue
        win = pygame.Rect(wx, wall.y + 10, 18, 6)
        surf.fill((60, 56, 52), win.inflate(2, 2))
        surf.fill((28, 34, 40), win)
        pygame.draw.line(surf, (64, 76, 88), (win.x + 2, win.bottom - 1), (win.x + 6, win.y))
        pygame.draw.line(surf, (64, 76, 88), (win.x + 5, win.bottom - 1), (win.x + 8, win.y + 2))
    surf.fill((60, 56, 52), door.inflate(2, 0))
    surf.fill((34, 42, 48), (door.x, door.y, 7, door.h))                  # стеклянные двери
    surf.fill((34, 42, 48), (door.x + 9, door.y, 7, door.h))
    glows.append(("window", door.centerx, door.centery))                  # внутри мигает лампа


def draw_car(surf, rect, body, broken, rnd):
    """Машина, вид сверху, капотом вправо."""
    surf.fill((22, 22, 25), rect.inflate(-2, -6).move(2, 3))              # тень
    b = rect.inflate(-2, -6)
    pygame.draw.rect(surf, shade(body, 0.55), b, border_radius=5)
    pygame.draw.rect(surf, body, b.inflate(-2, -2), border_radius=4)
    pygame.draw.line(surf, shade(body, 1.3), (b.x + 4, b.y + 2), (b.right - 5, b.y + 2))   # блик
    cabin = pygame.Rect(b.x + b.w * 3 // 10, b.y + 3, b.w * 4 // 10, b.h - 6)
    surf.fill(shade(body, 0.8), cabin)                                    # крыша
    glass = (110, 118, 124) if broken else (54, 68, 80)
    windshield = pygame.Rect(cabin.right, cabin.y + 1, 5, cabin.h - 2)
    rear = pygame.Rect(cabin.x - 4, cabin.y + 1, 4, cabin.h - 2)
    surf.fill(glass, windshield)
    surf.fill(shade(glass, 0.9), rear)
    if broken:                                                            # разбитое стекло
        cx, cy = windshield.centerx, windshield.centery
        for dx, dy in ((-2, -4), (2, -3), (2, 4), (-2, 3)):
            pygame.draw.line(surf, (60, 64, 70), (cx, cy), (cx + dx, cy + dy))
        for _ in range(12):                                               # ржавчина
            surf.fill((106, 70, 48), (rnd.randrange(b.x + 2, b.right - 3), rnd.randrange(b.y + 2, b.bottom - 3), 2, 1))
    else:
        surf.set_at((windshield.x + 1, windshield.y + 1), (120, 140, 156))
    surf.fill((200, 190, 130) if not broken else (70, 70, 64), (b.right - 2, b.y + 2, 2, 3))   # фары
    surf.fill((200, 190, 130), (b.right - 2, b.bottom - 5, 2, 3))
    surf.fill((110, 30, 30), (b.x, b.y + 2, 2, 3))                        # задние фонари
    surf.fill((110, 30, 30), (b.x, b.bottom - 5, 2, 3))


def draw_bin(surf, r):
    """Мусорный бак и пакет рядом."""
    body = pygame.Rect(r.x + 3, r.y + 3, 10, 11)
    surf.fill((24, 26, 25), body.move(1, 2))
    surf.fill((52, 62, 54), body)
    surf.fill((66, 78, 68), (body.x, body.y, body.w, 3))
    surf.fill((40, 48, 42), (body.x + 2, body.y + 5, 1, 5))
    surf.fill((40, 48, 42), (body.x + 6, body.y + 5, 1, 5))
    pygame.draw.ellipse(surf, (26, 26, 30), (r.x + 9, r.y + 10, 6, 5))   # чёрный пакет


def make_bush(rnd):
    """Куст — отдельная картинка (как дерево), чтобы за ним можно было пройти."""
    img = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    for cx, cy, rad, col in ((8, 9, 6, (28, 44, 30)), (5, 8, 4, (34, 54, 36)),
                             (11, 7, 4, (34, 54, 36)), (8, 5, 3, (42, 64, 42))):
        pygame.draw.circle(img, col, (cx, cy), rad)
    if rnd.random() < 0.4:
        img.set_at((6, 6), (90, 40, 40))                                  # ягодка
    return img


# ---------- ВЫСОКИЕ ПРЕДМЕТЫ ----------
# Деревья, фонари, будка и остановка выше клетки, на которой стоят.
# Поэтому их рисуем не в общей картинке карты, а отдельно — вместе с героем,
# по порядку "кто ниже на экране, тот рисуется позже". Так герой может
# зайти за дерево или фонарь.
def make_tree(rnd):
    s = pygame.Surface((28, 32), pygame.SRCALPHA)
    s.fill((52, 40, 32), (12, 20, 4, 11))                                 # ствол
    s.fill((40, 30, 26), (14, 20, 2, 11))
    if rnd.random() < 0.3:                                                # мёртвое дерево без листьев
        for (a, b) in (((14, 21), (6, 8)), ((14, 18), (22, 6)), ((14, 20), (14, 2)),
                       ((9, 12), (4, 10)), ((19, 11), (25, 12)), ((14, 10), (10, 3))):
            pygame.draw.line(s, (58, 48, 42), a, b)
        return s
    pygame.draw.circle(s, (18, 28, 20), (14, 13), 12)                    # тёмный край кроны
    pygame.draw.circle(s, (28, 44, 30), (14, 12), 11)
    for cx, cy, rad in ((10, 9, 5), (18, 10, 5), (13, 15, 5), (17, 16, 4)):
        pygame.draw.circle(s, (36, 56, 38), (cx, cy), rad)
    for cx, cy in ((9, 6), (16, 7), (12, 12)):
        pygame.draw.circle(s, (46, 68, 46), (cx, cy), 2)
    return s


def make_lamp(broken):
    s = pygame.Surface((12, 34), pygame.SRCALPHA)
    s.fill((34, 34, 38), (3, 30, 6, 4))                                   # основание
    s.fill((46, 46, 50), (5, 8, 2, 23))                                   # столб
    s.fill((70, 70, 76), (5, 8, 1, 23))
    pygame.draw.line(s, (46, 46, 50), (6, 8), (9, 5))                     # кронштейн
    s.fill((60, 60, 64), (6, 3, 6, 3))                                    # плафон
    s.fill((120, 110, 90) if broken else (236, 214, 150), (7, 6, 4, 1))   # лампочка
    return s


def make_booth():
    s = pygame.Surface((14, 28), pygame.SRCALPHA)
    s.fill((106, 34, 34), (1, 3, 12, 24))                                 # корпус
    s.fill((76, 22, 22), (0, 0, 14, 4))                                   # крыша
    s.fill((70, 86, 94), (3, 7, 8, 15))                                   # стекло
    pygame.draw.line(s, (106, 34, 34), (7, 7), (7, 21))
    s.fill((26, 26, 30), (4, 11, 3, 4))                                   # телефон
    s.fill((210, 200, 150), (6, 1, 2, 1))                                 # лампочка сверху
    s.fill((60, 18, 18), (1, 25, 12, 2))
    return s


def make_bus_stop(w):
    """Остановка смотрит на дорогу (вверх), а сзади, со стороны парка, у неё стеклянная стенка.
    Две картинки: bench — скамейка; front — крыша, стойки и заднее стекло
    (стекло ближе всего к нам, поэтому рисуется поверх скамейки и героя под крышей)."""
    bench = pygame.Surface((w, 30), pygame.SRCALPHA)
    bench.fill((92, 72, 54), (8, 17, w - 34, 3))                           # сиденье
    bench.fill((60, 46, 36), (8, 20, w - 34, 1))
    bench.fill((40, 42, 46), (10, 21, 1, 4))                               # ножки
    bench.fill((40, 42, 46), (w - 28, 21, 1, 4))
    front = pygame.Surface((w, 30), pygame.SRCALPHA)
    front.fill((96, 112, 122, 110), (3, 10, w - 6, 19))                    # заднее стекло (со стороны парка)
    pygame.draw.rect(front, (52, 56, 62), (3, 10, w - 6, 19), 1)
    front.fill((140, 120, 96), (w - 18, 12, 12, 10))                       # выцветший плакат на стекле
    front.fill((80, 60, 52), (w - 15, 14, 6, 4))
    front.fill((40, 42, 46), (2, 2, 2, 27))                                # левая стойка
    front.fill((40, 42, 46), (w - 4, 2, 2, 27))                            # правая стойка
    front.fill((70, 72, 78), (0, 0, w, 5))                                 # крыша
    front.fill((50, 52, 58), (0, 4, w, 1))
    return bench, front


# ---------- ПРЕДМЕТЫ, КОТОРЫЕ МОЖНО ПОДНЯТЬ ----------
# ---------- ПЛЫВУЩИЕ КЛОЧЬЯ ТУМАНА ----------
def draw_fog_clouds(surf, clouds, cam_x, cam_y, t, offset=(0, 0), special_flags=0):
    """Картинка-узор с клочьями тумана повторяется плиткой по всему экрану и медленно едет.
    Два слоя с разной скоростью — так туман выглядит объёмнее.
    offset — если рисуем не на весь экран, а на кусочек, который на экране стоит в точке offset."""
    w, h = clouds.get_size()
    sx, sy = FOG_CLOUDS_SPEED
    # (скорость слоя, насколько он "ближе" к камере, сдвиг узора — чтобы слои не совпадали)
    for speed, depth, shift in ((1.0, 1.0, 0), (0.6, 1.2, 90)):
        # Где начинается узор: туман привязан к миру (cam) и плывёт со временем (t).
        # % w — узор повторяется, поэтому сдвиг больше ширины картинки не нужен
        ox = round(-cam_x * depth + t * sx * speed + shift) % w
        oy = round(-cam_y * depth + t * sy * speed + shift) % h
        for x in range(ox - w, GAME_W, w):
            for y in range(oy - h, GAME_H, h):
                surf.blit(clouds, (x - offset[0], y - offset[1]), special_flags=special_flags)


# ---------- КАРТИНКИ ПРЕДМЕТОВ ----------
_item_images = {}   # уже загруженные картинки, чтобы не читать файл каждый кадр


def item_image(name):
    """Картинка из data/items/<name>.png. Загружается один раз, потом берётся из памяти.
    Если файла нет — вместо него ярко-розовый квадрат, чтобы сразу было заметно."""
    if name not in _item_images:
        path = os.path.join(DATA_DIR, "items", name + ".png")
        if os.path.exists(path):
            _item_images[name] = pygame.image.load(path).convert_alpha()
        else:
            print(f"Нет картинки data/items/{name}.png")
            missing = pygame.Surface((16, 16))
            missing.fill((255, 0, 255))
            _item_images[name] = missing
    return _item_images[name]


def draw_pipe_item(surf, r):
    """Железная труба на земле."""
    surf.blit(item_image("pipe_ground"), (r.x, r.y))


def draw_glint(surf, x, y, time_total):
    """Искорка над предметом, который можно поднять, — рисуется ПОСЛЕ тумана, поэтому её видно издалека.
    Вспыхивает примерно раз в полторы секунды."""
    t = (time_total * 0.7) % 1
    if t < 0.12:
        size = 3 if t < 0.06 else 2
        c = (255, 255, 240)
        surf.fill(c, (x - size, y, size * 2 + 1, 1))   # горизонтальный лучик
        surf.fill(c, (x, y - size, 1, size * 2 + 1))   # вертикальный лучик


# ---------- ВНУТРИ ПОМЕЩЕНИЙ ----------
def draw_shelf(surf, rect, rnd):
    """Стеллаж с товарами: сверху полка, спереди два ряда банок и коробок."""
    surf.fill((20, 20, 22), rect.move(2, 3))                              # тень
    surf.fill((84, 86, 92), rect)                                         # металлический корпус
    surf.fill((110, 112, 118), (rect.x, rect.y, rect.w, 3))               # верхняя полка
    for shelf_y in (rect.y + 4, rect.y + 10):                             # два ряда товаров
        surf.fill((52, 54, 58), (rect.x + 1, shelf_y, rect.w - 2, 5))     # глубина полки
        x = rect.x + 2
        while x < rect.right - 4:
            w = rnd.choice((2, 3, 3, 4))
            if rnd.random() < 0.75:                                       # иногда — пустое место
                color = rnd.choice([(120, 46, 42), (60, 90, 120), (150, 130, 70), (70, 110, 70), (140, 140, 130)])
                hgt = rnd.randint(3, 5)
                surf.fill(color, (x, shelf_y + 5 - hgt, w, hgt))
                surf.fill(shade(color, 1.3), (x, shelf_y + 5 - hgt, w, 1))   # блик сверху
            x += w + 1
    pygame.draw.rect(surf, (40, 42, 46), rect, 1)                          # контур
    if rnd.random() < 0.6:                                                # что-то упало на пол
        fx = rnd.randrange(rect.x, rect.right - 4)
        surf.fill(rnd.choice([(120, 46, 42), (150, 130, 70)]), (fx, rect.bottom + rnd.randint(2, 6), 4, 3))


def make_counter(rect, rnd, glows):
    """Прилавок с кассой — отдельная картинка (как дерево или фонарь),
    поэтому герой может пройти ЗА ним: тогда прилавок закрывает его ноги."""
    img = pygame.Surface((rect.w, rect.h + 4), pygame.SRCALPHA)   # +4 пикселя сверху: касса выше прилавка
    c = pygame.Rect(0, 4, rect.w, rect.h)                          # сам прилавок внутри картинки
    img.fill((92, 68, 50), c)                                      # дерево
    img.fill((120, 92, 68), (c.x, c.y, c.w, 5))                    # столешница
    img.fill((70, 52, 38), (c.x, c.bottom - 3, c.w, 3))
    pygame.draw.rect(img, (50, 36, 28), c, 1)
    reg = pygame.Rect(c.right - 18, 0, 12, 8)                      # касса
    img.fill((60, 60, 66), reg)
    img.fill((40, 40, 44), (reg.x, reg.bottom - 2, reg.w, 2))
    img.fill((70, 140, 90), (reg.x + 2, reg.y + 1, 6, 3))          # зелёный экранчик
    glows.append(("booth", rect.x + reg.x + 5, rect.y - 4 + reg.y + 2))
    for _ in range(3):                                             # раскиданные чеки
        img.fill((200, 196, 186), (rnd.randrange(c.x + 2, c.right - 22), c.y + rnd.randint(1, 3), 3, 2))
    return img


def draw_fridge(surf, rect, rnd, glows):
    """Холодильники со стеклянными дверцами и холодным светом. Они выше клетки — заходят на стену."""
    body = pygame.Rect(rect.x, rect.y - 10, rect.w, rect.h + 10)
    surf.fill((20, 20, 22), body.move(2, 2))
    surf.fill((150, 156, 160), body)                                      # белый корпус
    for dx in range(0, rect.w, TILE):                                     # по дверце на каждую клетку
        glass = pygame.Rect(rect.x + dx + 2, body.y + 3, 12, body.h - 6)
        surf.fill((70, 100, 112), glass)
        for by in range(glass.y + 2, glass.bottom - 2, 5):                # полки с бутылками
            pygame.draw.line(surf, (100, 130, 140), (glass.x, by + 4), (glass.right - 1, by + 4))
            for bx in range(glass.x + 1, glass.right - 1, 3):
                if rnd.random() < 0.6:
                    surf.fill(rnd.choice([(40, 70, 50), (120, 60, 50), (90, 90, 120)]), (bx, by, 2, 4))
        pygame.draw.line(surf, (200, 230, 240), (glass.x + 1, glass.y + 1), (glass.x + 1, glass.bottom - 2))  # блик
        glows.append(("fridge", glass.centerx, glass.centery))
    pygame.draw.rect(surf, (90, 94, 98), body, 1)


def draw_exit_door(surf, r):
    """Выход в нижней стене: тёмный проём, полоска света из-под двери и коврик."""
    surf.fill((30, 26, 24), r)
    surf.fill((150, 150, 158), (r.x + 2, r.bottom - 3, TILE - 4, 3))     # свет с улицы
    surf.fill((70, 40, 36), (r.x + 1, r.y - 6, TILE - 2, 6))             # коврик на полу перед дверью
    for i in range(r.x + 2, r.right - 2, 2):
        surf.set_at((i, r.y - 3), (90, 54, 48))


def draw_back_door(surf, r):
    """Запертая дверь в подсобку (на стене)."""
    door = pygame.Rect(r.x + 2, r.y + 1, TILE - 4, TILE - 4)
    surf.fill((56, 40, 32), door)
    pygame.draw.rect(surf, (36, 26, 22), door, 1)
    surf.fill((200, 196, 180), (door.x + 3, door.y + 3, 6, 3))           # табличка
    surf.set_at((door.right - 3, door.centery + 1), (170, 150, 90))      # ручка


def build_world(rows):
    """Рисует всю землю и постройки в одну большую картинку (один раз при запуске)
    и собирает список высоких предметов и источников света."""
    rnd = random.Random(7)   # фиксированное "зерно" — карта всегда выглядит одинаково
    w = len(rows[0]) * TILE
    h = len(rows) * TILE
    surf = pygame.Surface((w, h))
    props = []    # высокие предметы: (нижний край, картинка, x, y)
    glows = []    # источники света: (вид, x, y)

    draw_ground(surf, rows, rnd)

    lamp_pool = make_glow(26, (46, 40, 22))       # светлое пятно на земле под фонарём
    fence_img = make_fence()                      # кусок забора (один на все клетки)

    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            r = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
            if ch == "b":
                pygame.draw.ellipse(surf, (26, 34, 27), (r.x + 1, r.y + 9, 15, 6))   # тень куста — на земле
                props.append((r.bottom - 2, make_bush(rnd), r.x, r.y))
            elif ch == "X":
                draw_bin(surf, r)
            elif ch == "T":
                pygame.draw.ellipse(surf, (24, 32, 26), (r.x - 3, r.bottom - 8, 22, 8))   # тень
                img = make_tree(rnd)
                props.append((r.bottom, img, r.centerx - 14, r.bottom - 32))
            elif ch == "#" and fence_is_horizontal(rows, x, y):
                props.append((r.bottom - 3, fence_img, r.x, r.y))
            elif ch in "Ll":
                broken = ch == "l"
                if not broken:
                    surf.blit(lamp_pool, (r.centerx - 26, r.bottom - 30), special_flags=pygame.BLEND_RGB_ADD)
                props.append((r.bottom, make_lamp(broken), r.centerx - 6, r.bottom - 34))
                glows.append(("lamp_broken" if broken else "lamp", r.centerx + 3, r.bottom - 29))
            elif ch == "F":
                pygame.draw.ellipse(surf, (30, 30, 34), (r.x, r.bottom - 6, 18, 6))
                props.append((r.bottom, make_booth(), r.centerx - 7, r.bottom - 28))
                glows.append(("booth", r.centerx, r.bottom - 27))
            elif ch == "*":                                # лампа на потолке (мигает)
                surf.blit(lamp_pool, (r.centerx - 26, r.centery - 26), special_flags=pygame.BLEND_RGB_ADD)
                glows.append(("lamp_broken", r.centerx, r.centery))
            elif ch == "D":
                draw_exit_door(surf, r)
            elif ch == "G":
                draw_back_door(surf, r)

    for rect in find_groups(rows, "H"):
        draw_house(surf, rect, rnd, glows)
    for rect in find_groups(rows, "K"):
        draw_shop(surf, rect, rnd, glows)
    for rect in find_groups(rows, "C"):
        draw_car(surf, rect, (112, 32, 34), False, rnd)                  # машина героя
    for rect in find_groups(rows, "c"):
        draw_car(surf, rect, rnd.choice([(70, 80, 90), (90, 86, 70), (60, 70, 62)]), True, rnd)
    for rect in find_groups(rows, "B"):
        bench, front = make_bus_stop(rect.w)
        props.append((rect.y + 11, bench, rect.x, rect.bottom - 30))  # скамейка — "линия" у её ножек
        props.append((rect.bottom, front, rect.x, rect.bottom - 30))  # крыша, стойки и заднее стекло
    for rect in find_groups(rows, "S"):
        draw_shelf(surf, rect, rnd)
    for rect in find_groups(rows, "R"):
        surf.fill((20, 20, 22), rect.move(2, 3))                   # тень прилавка — на полу
        props.append((rect.bottom, make_counter(rect, rnd, glows), rect.x, rect.y - 4))
    for rect in find_groups(rows, "Q"):
        draw_fridge(surf, rect, rnd, glows)

    return surf, props, glows


# ---------- ТУМАН (тоже создаётся один раз) ----------
def make_fog(color, clear, full, max_alpha):
    """Большая картинка тумана (или темноты) с прозрачной 'дыркой' в центре.
    Центр дырки потом ставим на героя — вокруг него туман рассеивается.
    clear — радиус, где видно чётко; full — дальше него сплошной туман; max_alpha — его плотность."""
    fog = pygame.Surface((GAME_W * 2, GAME_H * 2), pygame.SRCALPHA)
    fog.fill((*color, max_alpha))
    cx, cy = GAME_W, GAME_H
    rnd = random.Random(1)
    # Для каждого пикселя внутри круга считаем точное расстояние до центра —
    # так прозрачность меняется плавно, без колец и "ступенек"
    for y in range(max(0, cy - full), min(GAME_H * 2, cy + full + 1)):
        for x in range(max(0, cx - full), min(GAME_W * 2, cx + full + 1)):
            d = math.hypot(x - cx, y - cy)
            if d >= full:
                continue
            alpha = max_alpha * smootherstep(clear, full, d)
            alpha += rnd.uniform(-1.5, 1.5)          # крошечный шум прячет переходы между оттенками
            fog.set_at((x, y), (*color, max(0, min(255, round(alpha)))))
    return fog


# ---------- ФОНАРИК (картинки создаются один раз) ----------
FLASH_DIRS = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}
# Откуда выходит луч относительно центра героя — из стекла фонарика в левой руке
FLASH_ORIGIN = {"right": (5, -4), "left": (-5, -4), "down": (6, -1), "up": (-7, -7)}


def smootherstep(edge0, edge1, x):
    """Как smoothstep, но ещё мягче у краёв — переход совсем незаметный."""
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * t * (t * (t * 6 - 15) + 10)


def smoothstep(edge0, edge1, x):
    """Плавный переход: 0, когда x у edge0, и 1, когда x у edge1.
    В отличие от прямой линии, начинается и заканчивается мягко — без заметного "излома"."""
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def flash_strength(along, s):
    """Насколько ярко светит фонарик в точке: along — расстояние вдоль луча,
    s — смещение вбок от его середины. Возвращает число от 0 (темно) до 1 (ярко)."""
    if along <= 0:
        return 0.0
    half = along * math.tan(math.radians(FLASH_ANGLE)) + 3   # ширина конуса на этом расстоянии
    side = abs(s) / half                                      # 0 — середина луча, 1 — край
    edge = smoothstep(1.0, 1.0 - FLASH_SOFT, side)            # к краю свет плавно гаснет
    far = smoothstep(FLASH_RANGE, FLASH_CLEAR, along)         # и вдали тоже
    near = min(1.0, along / 10)                               # у самой руки слабый — чтобы не "засветить" героя
    return edge * far * near


def make_flashlight(fog_base, color, max_alpha):
    """Для каждого из 4 направлений готовим три картинки:
    fog   — туман, в котором кроме круга вырезан ещё и конус луча;
    light — тёплый свет на земле и предметах (рисуется ДО тумана);
    beam  — слабое свечение самого тумана в луче (рисуется ПОСЛЕ тумана)."""
    R = FLASH_RANGE
    result = {}
    for name, (dx, dy) in FLASH_DIRS.items():
        hx, hy = FLASH_ORIGIN[name]
        fog = fog_base.copy()
        light = pygame.Surface((R * 2, R * 2))   # центр картинки (R, R) — это рука героя
        light.fill((0, 0, 0))
        beam = pygame.Surface((R * 2, R * 2))
        beam.fill((0, 0, 0))

        # Проверяем каждый пиксель квадрата вокруг руки и точно считаем,
        # где он относительно луча (без округлений — поэтому края ровные)
        for oy in range(-R + 1, R):
            for ox in range(-R + 1, R):
                along = ox * dx + oy * dy          # расстояние вдоль луча
                s = -ox * dy + oy * dx             # смещение вбок
                k = flash_strength(along, s)
                if k < 0.01:
                    continue

                # Туман: чем ярче свет, тем прозрачнее
                fx, fy = GAME_W + hx + ox, GAME_H + hy + oy
                new_alpha = int(max_alpha * (1 - k))
                if new_alpha < fog.get_at((fx, fy))[3]:
                    fog.set_at((fx, fy), (*color, new_alpha))

                glow = k * (1 - 0.5 * along / R)
                light.set_at((R + ox, R + oy), (int(64 * glow), int(54 * glow), int(34 * glow)))
                beam.set_at((R + ox, R + oy), (int(26 * glow), int(25 * glow), int(20 * glow)))
        result[name] = (fog, light, beam)
    return result


# ---------- ФОНАРИК НЕ СВЕТИТ СКВОЗЬ ПРЕДМЕТЫ ----------
# Сколько пикселей луч может пройти "внутрь" предмета, прежде чем упрётся.
# Так луч освещает переднюю стенку предмета (фасад дома, забор, бок машины), а дальше — тень.
LIGHT_FREE = 255                    # здесь ничего нет — луч идёт дальше
LIGHT_PASS = {
    "C": 6, "c": 6,                 # машины: освещается ближний бок
    "F": 8,                         # телефонная будка
    "X": 4,                         # мусорный бак
    "W": 16, "D": 16, "G": 16,      # стены магазина и двери в них
    "S": 8, "Q": 8, "R": 8,         # стеллажи, холодильники, прилавок
}
FENCE_PASS = 14                     # забор "слева направо": освещается, а за ним — тень
WALL_PASS = 2                       # заборы столбиком и края карты
HOUSE_FACADE = {"H": 14, "K": 18}   # дома и магазин: фасад освещается, крыша — нет
FLASH_RAYS = 48                     # сколько лучей проверяем (больше — точнее, но медленнее)


def make_light_grid(rows):
    """Для каждого пикселя локации запоминаем, сколько луч может в нём пройти (делается один раз).
    Возвращает (bytearray — числа подряд, строка за строкой; ширина карты в пикселях)."""
    w, h = len(rows[0]) * TILE, len(rows) * TILE
    grid = bytearray([LIGHT_FREE]) * (w * h)

    def mark(rect, value):
        for y in range(max(0, rect.top), min(h, rect.bottom)):
            start = y * w + max(0, rect.left)
            end = y * w + min(w, rect.right)
            grid[start:end] = bytes([value]) * (end - start)

    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            r = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
            if ch in LIGHT_PASS:
                mark(r, LIGHT_PASS[ch])
            elif ch == "#":
                mark(r, FENCE_PASS if fence_is_horizontal(rows, x, y) else WALL_PASS)
    for letter, facade in HOUSE_FACADE.items():
        for r in find_groups(rows, letter):
            mark(r, 0)                                                         # крыша: свет сразу гаснет
            mark(pygame.Rect(r.x, r.bottom - facade, r.w, facade), facade + 2)  # фасад освещается
    return grid, w


def flash_reach(light_grid, x, y, angle):
    """Как далеко пройдёт луч из точки (x, y) под углом angle, пока не упрётся в предмет."""
    grid, w = light_grid
    h = len(grid) // w
    dx, dy = math.cos(angle), math.sin(angle)
    depth = 0                                     # сколько пикселей луч уже идёт внутри предмета
    for d in range(3, FLASH_RANGE):
        px, py = int(x + dx * d), int(y + dy * d)
        if not (0 <= px < w and 0 <= py < h):
            return d
        limit = grid[py * w + px]
        if limit == LIGHT_FREE:
            depth = 0
        else:
            depth += 1
            if depth > limit:
                return d                          # упёрся — дальше тень
    return FLASH_RANGE


def occlude_flashlight(light_grid, fog_base, fog_img, light, beam, hand_x, hand_y, facing, hx, hy):
    """Обрезает луч фонарика там, где он упирается в предметы. Возвращает новые fog_img, light, beam.
    hand_x, hand_y — где фонарик на карте; hx, hy — сдвиг руки от центра героя (FLASH_ORIGIN)."""
    R = FLASH_RANGE
    dx, dy = FLASH_DIRS[facing]
    base = math.atan2(dy, dx)
    spread = math.radians(FLASH_ANGLE + 10)

    # 1. Многоугольник "куда дошёл свет": от руки — к концу каждого луча
    points = [(R, R)]
    blocked = False
    for i in range(FLASH_RAYS + 1):
        a = base - spread + 2 * spread * i / FLASH_RAYS
        reach = flash_reach(light_grid, hand_x, hand_y, a)
        blocked = blocked or reach < R
        points.append((R + math.cos(a) * reach, R + math.sin(a) * reach))
    if not blocked:
        return fog_img, light, beam               # луч ни во что не упёрся — ничего не меняем

    # 2. Маска: белое — свет есть, прозрачное — нет. Размываем, чтобы край тени был мягким
    lit = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)
    pygame.draw.polygon(lit, (255, 255, 255, 255), points)
    lit = pygame.transform.smoothscale(lit, (R // 2, R // 2))
    lit = pygame.transform.smoothscale(lit, (R * 2, R * 2))
    dark = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)       # обратная маска: 1 - lit
    dark.fill((255, 255, 255, 255))
    dark.blit(lit, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    # 3. Свет на земле и свечение тумана — только там, куда дошёл луч
    light = light.copy()
    light.blit(lit, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    beam = beam.copy()
    beam.blit(lit, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    # 4. Туман: внутри луча — туман с вырезанным конусом, за предметом — обычный туман
    square = pygame.Rect(GAME_W + hx - R, GAME_H + hy - R, R * 2, R * 2).clip(fog_img.get_rect())
    part = pygame.Rect(square.x - (GAME_W + hx - R), square.y - (GAME_H + hy - R), square.w, square.h)
    cone = fog_img.subsurface(square).copy()
    cone.blit(lit, (0, 0), part, special_flags=pygame.BLEND_RGBA_MULT)
    plain = fog_base.subsurface(square).copy()
    plain.blit(dark, (0, 0), part, special_flags=pygame.BLEND_RGBA_MULT)
    plain.blit(cone, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)      # склеиваем две части
    fog_img = fog_img.copy()
    fog_img.fill((0, 0, 0, 0), square)
    fog_img.blit(plain, square.topleft, special_flags=pygame.BLEND_RGBA_ADD)
    return fog_img, light, beam


# ---------- ТЁМНЫЕ КРАЯ ЭКРАНА (страх) ----------
def make_vignette():
    """Тёмно-красная рамка по краям экрана: в центре прозрачно, к краям — темнее."""
    vig = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
    cx, cy = GAME_W / 2, GAME_H / 2
    for y in range(GAME_H):
        for x in range(GAME_W):
            # расстояние до центра, "сплющенное" под форму экрана: 0 — центр, 1 — угол
            d = math.hypot((x - cx) / cx, (y - cy) / cy) / math.sqrt(2)
            a = smoothstep(0.35, 1.0, d)
            vig.set_at((x, y), (30, 0, 4, int(255 * a)))
    return vig

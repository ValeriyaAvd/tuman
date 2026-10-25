# =====================================================
#  world.py — свечение, клочья тумана, предметы на земле,
#  туман и луч фонарика. Сами карты загружает tiled_map.py.
# =====================================================

import os
import math
import random
import pygame
from settings import *

# Земля под ногами героя (буквы в сетке, которую строит tiled_map.py)
GRASS_TILES = ","

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


# ---------- ПЛЫВУЩИЕ КЛОЧЬЯ ТУМАНА ----------
def draw_fog_clouds(surf, clouds, cam_x, cam_y, t, offset=(0, 0), special_flags=0):
    """Картинка-узор с клочьями тумана повторяется плиткой по всему экрану и медленно едет.
    Два слоя с разной скоростью — так туман выглядит объёмнее.
    offset — если рисуем не на весь экран, а на кусочек, который на экране стоит в точке offset."""
    w, h = (v // ART_SCALE for v in clouds.get_size())
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
    surf.blit(item_image("pipe_ground"), (r.x, r.y))                                  # ржавчина


def draw_glint(surf, x, y, time_total):
    """Искорка над предметом, который можно поднять, — рисуется ПОСЛЕ тумана, поэтому её видно издалека.
    Вспыхивает примерно раз в полторы секунды."""
    t = (time_total * 0.7) % 1
    if t < 0.12:
        size = 3 if t < 0.06 else 2
        c = (255, 255, 240)
        surf.fill(c, (x - size, y, size * 2 + 1, 1))   # горизонтальный лучик
        surf.fill(c, (x, y - size, 1, size * 2 + 1))   # вертикальный лучик


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
# Откуда выходит луч относительно центра героя (из руки, а не из ног)
FLASH_ORIGIN = {"right": (6, -4), "left": (-6, -4), "down": (5, -1), "up": (-6, -7)}


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
# Сами значения задаются в Tiled (collision / light_blocker / light_facade).
LIGHT_FREE = 255                    # здесь ничего нет — луч идёт дальше
WALL_PASS = 2                       # стены без своего light_pass
FLASH_RAYS = 48                     # сколько лучей проверяем (больше — точнее, но медленнее)


def make_light_grid(rows, regions=()):
    """Для каждого пикселя локации запоминаем, сколько луч может в нём пройти (делается один раз).
    regions — список (прямоугольник, сколько луч проходит), его собирает locations.py из карты Tiled.
    Возвращает (bytearray — числа подряд, строка за строкой; ширина карты в пикселях)."""
    w, h = len(rows[0]) * TILE, len(rows) * TILE
    grid = bytearray([LIGHT_FREE]) * (w * h)
    for rect, value in regions:
        for y in range(max(0, rect.top), min(h, rect.bottom)):
            start = y * w + max(0, rect.left)
            end = y * w + min(w, rect.right)
            grid[start:end] = bytes([value]) * (end - start)
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
    lit = pygame.transform.smoothscale(lit, (R * 2 * ART_SCALE, R * 2 * ART_SCALE))
    dark = pygame.Surface((R * 2 * ART_SCALE, R * 2 * ART_SCALE), pygame.SRCALPHA)       # обратная маска: 1 - lit
    dark.fill((255, 255, 255, 255))
    dark.blit(lit, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    # 3. Свет на земле и свечение тумана — только там, куда дошёл луч
    light = light.copy()
    light.blit(lit, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    beam = beam.copy()
    beam.blit(lit, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    # 4. Туман: внутри луча — туман с вырезанным конусом, за предметом — обычный туман
    square = pygame.Rect(round((GAME_W + hx - R) * ART_SCALE), round((GAME_H + hy - R) * ART_SCALE),
                         R * 2 * ART_SCALE, R * 2 * ART_SCALE).clip(fog_img.get_rect())
    part = pygame.Rect(square.x - round((GAME_W + hx - R) * ART_SCALE),
                       square.y - round((GAME_H + hy - R) * ART_SCALE), square.w, square.h)
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

# =====================================================
#  locations.py — локации игры (улица, магазин...) и двери между ними.
#  Чтобы добавить новую локацию: нарисуй её карту в папке data,
#  добавь строку в LOCATIONS и двери туда и обратно в DOORS.
# =====================================================

import pygame
from settings import *
from world import load_map, build_world, find_groups, make_fog, make_flashlight
from characters import Monster
from story import build_spots, build_remarks

# Все локации: имя -> (файл карты в папке data, внутри помещения?)
# Внутри помещений вместо тумана — темнота.
LOCATIONS = {
    "street": ("map.txt", False),
    "shop": ("shop.txt", True),
}

# Двери: (откуда, клетка x, клетка y, ширина в клетках,
#         куда, клетка x, клетка y, куда смотрит герой, подсказка)
# Клетка "откуда" — это место ПЕРЕД дверью, где нужно стоять и нажать E.
DOORS = [
    ("street", 25, 32, 2, "shop", 7, 10, "up", "[E] войти в магазин"),
    ("shop", 7, 10, 1, "street", 25, 32, "down", "[E] выйти на улицу"),
]


class Door:
    def __init__(self, x, y, width, target, tx, ty, facing, hint):
        self.zone = pygame.Rect(x * TILE, y * TILE, width * TILE, TILE)   # где стоять, чтобы войти
        self.target = target                                            # имя локации, куда ведёт
        self.arrive = (tx * TILE + 4, ty * TILE + 8)                    # где герой окажется
        self.facing = facing
        self.hint = hint


class Location:
    """Всё, что относится к одной локации: карта, картинка, свет, монстры, двери."""

    def __init__(self, name, map_file, inside, monster_frames, fogs):
        self.name = name
        self.inside = inside
        self.rows, self.walls, self.start, self.note_rect, monster_starts = load_map(map_file)
        self.map_surf, self.props, self.glows = build_world(self.rows)
        self.fog, self.flashlight = fogs["inside" if inside else "outside"]
        self.fog_full = FOG_INSIDE_FULL if inside else FOG_FULL   # как далеко видно без фонарика
        self.car_rects = find_groups(self.rows, "C")
        self.pipe_rects = find_groups(self.rows, "I")    # где лежит труба
        self.spots = build_spots(self.rows)
        self.remarks = build_remarks(name)
        self.monsters = [Monster(pos, monster_frames) for pos in monster_starts]
        self.doors = [Door(x, y, w, to, tx, ty, facing, hint)
                      for frm, x, y, w, to, tx, ty, facing, hint in DOORS if frm == name]


def build_locations(monster_frames):
    """Создаёт все локации один раз при запуске игры."""
    fog_out = make_fog(FOG_COLOR, FOG_CLEAR, FOG_FULL, FOG_MAX_ALPHA)                           # туман на улице
    fog_in = make_fog(FOG_INSIDE_COLOR, FOG_INSIDE_CLEAR, FOG_INSIDE_FULL, FOG_INSIDE_ALPHA)   # темнота внутри
    fogs = {
        "outside": (fog_out, make_flashlight(fog_out, FOG_COLOR, FOG_MAX_ALPHA)),
        "inside": (fog_in, make_flashlight(fog_in, FOG_INSIDE_COLOR, FOG_INSIDE_ALPHA)),
    }
    return {name: Location(name, map_file, inside, monster_frames, fogs)
            for name, (map_file, inside) in LOCATIONS.items()}

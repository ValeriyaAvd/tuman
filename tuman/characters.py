# =====================================================
#  characters.py — герой и монстры: загрузка картинок, движение, анимация.
#  Картинки лежат в data/hero.png и data/monster.png.
# =====================================================

import os
import math
import random
import pygame
from settings import *
from world import flash_strength, FLASH_DIRS, FLASH_ORIGIN, item_image

# ---------- КАРТИНКИ ПЕРСОНАЖЕЙ ----------
# hero.png — лист кадров героя. Каждый кадр 12x19 пикселей.
#   1-я строка — идёт вниз, 2-я — вверх, 3-я — вправо (влево — это зеркальное "вправо").
#   В каждой строке 5 кадров: 1-й — стоит, остальные 4 — шаги по очереди.
# monster.png — 2 кадра монстра 12x20: стоит и шагает.
HERO_W, HERO_H = 17, 26
MON_W, MON_H = 12, 20


def load_image(name):
    """Загружает картинку из папки data (с прозрачностью)."""
    return pygame.image.load(os.path.join(DATA_DIR, name)).convert_alpha()


def cut_frames(sheet, w, h):
    """Режет лист на кадры размером w x h. Возвращает список строк, в каждой — список кадров."""
    return [[sheet.subsurface((x * w, y * h, w, h)) for x in range(sheet.get_width() // w)]
            for y in range(sheet.get_height() // h)]


def build_hero_frames():
    """Кадры героя: для каждого направления — кадр стояния и список кадров ходьбы."""
    rows = cut_frames(load_image("hero.png"), HERO_W, HERO_H)
    frames = {}
    for direction, row in zip(("down", "up", "right"), rows):
        frames[direction] = {"stand": row[0], "walk": row[1:]}
    # Влево — это просто зеркальное отражение вправо
    flip = lambda img: pygame.transform.flip(img, True, False)
    frames["left"] = {
        "stand": flip(frames["right"]["stand"]),
        "walk": [flip(f) for f in frames["right"]["walk"]],
    }
    return frames


def build_monster_frames():
    """Кадры монстра: для взгляда вправо (False) и влево (True — зеркально)."""
    stand, step = cut_frames(load_image("monster.png"), MON_W, MON_H)[0][:2]
    flip = lambda img: pygame.transform.flip(img, True, False)
    corpse = pygame.transform.rotate(stand, 90)                       # убитый монстр лежит на боку
    # Мёртвое тело блёклое: цвета почти серые, тёмные, как асфальт, и чуть просвечивают
    for x in range(corpse.get_width()):
        for y in range(corpse.get_height()):
            r, g, b, a = corpse.get_at((x, y))
            if a == 0:
                continue                                   # прозрачный пиксель — пропускаем
            grey = (r + g + b) // 3                        # яркость пикселя без цвета
            if r > g + 40:                                 # кровь — оставляем тёмно-бурой
                color = (58 + r // 8, 34, 34)
            else:                                          # остальное — смешиваем с цветом асфальта
                v = 26 + grey // 4                         # все оттенки сжимаем в узкий тёмный диапазон
                color = (v, v, v + 3)
            corpse.set_at((x, y), (*color, a * 9 // 10))
    return {
        False: {"stand": stand, "walk": [step, stand]},
        True: {"stand": flip(stand), "walk": [flip(step), flip(stand)]},
        "corpse": corpse,
    }


def build_hero_hd_frames():
    """Детальные кадры героя (data/hero_hd.png): рисуются поверх мира в высоком разрешении.
    Если файла нет — возвращаем None, и герой рисуется обычным пиксельным."""
    path = os.path.join(DATA_DIR, "hero_hd.png")
    if not os.path.exists(path):
        return None
    sheet = pygame.image.load(path).convert_alpha()
    size = (HERO_W * ZOOM, HERO_H * ZOOM)          # на большом холсте герой в ZOOM раз больше
    rows = cut_frames(sheet, sheet.get_width() // 5, sheet.get_height() // 3)
    rows = [[pygame.transform.smoothscale(f, size) for f in row] for row in rows]
    frames = {}
    for direction, row in zip(("down", "up", "right"), rows):
        frames[direction] = {"stand": row[0], "walk": row[1:]}
    flip = lambda img: pygame.transform.flip(img, True, False)
    frames["left"] = {"stand": flip(frames["right"]["stand"]), "walk": [flip(f) for f in frames["right"]["walk"]]}
    return frames


# ---------- ГЕРОЙ ----------
class Player:
    hd_frames = None    # детальные кадры (если есть) — задаются один раз в main.py

    def __init__(self, pos, frames, hp=3):
        # "Хитбокс" — невидимый прямоугольник у ног героя, по нему считаются столкновения
        # Ширина — как у самой фигурки (12), чтобы герой не "залезал" краями на стены.
        # pos[0] - 2 — чтобы середина осталась там же, где была при старой ширине 8
        self.rect = pygame.Rect(pos[0] - 2, pos[1], 12, 6)
        self.frames = frames                               # все кадры анимации
        self.x = float(self.rect.x)                        # точная позиция (дробная)
        self.y = float(self.rect.y)
        self.facing = "right"
        self.walk_time = 0.0
        self.moving = False
        self.stepped = False                               # сделал ли шаг в этом кадре
        self.tremble = False                               # дрожит от страха?
        self.stamina = 1.0                                 # выносливость: 1 — полная, 0 — выдохся
        self.tired = False                                 # выдохся — бежать нельзя, пока не отдышится
        self.running = False                               # бежит ли сейчас
        self.left_hand = None                              # что в левой руке: None или "flashlight"
        self.right_hand = None                             # что в правой руке: None или "pipe"
        self.light_on = False                              # горит ли фонарик (для стекла фонарика)
        self.swing = None                                  # ход удара: None — не бьёт, 0…1 — бьёт
        self.max_hp = hp                                   # здоровье: сколько ударов монстра выдержит
        self.hp = hp
        self.hurt = 0.0                                    # сколько ещё секунд неуязвим после удара

    def update(self, dt, keys, walls):
        self.hurt = max(0.0, self.hurt - dt)
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])

        self.moving = dx != 0 or dy != 0
        if dx and dy:            # по диагонали не должен ходить быстрее
            dx *= 0.7071
            dy *= 0.7071

        if dy > 0: self.facing = "down"
        if dy < 0: self.facing = "up"
        if dx > 0: self.facing = "right"
        if dx < 0: self.facing = "left"

        # Бег: Shift зажат, герой двигается и ещё не выдохся
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        self.running = shift and self.moving and not self.tired
        if self.running:
            self.stamina -= STAMINA_DRAIN * dt
            if self.stamina <= 0:
                self.stamina = 0
                self.tired = True                  # выдохся!
        else:
            self.stamina = min(1.0, self.stamina + STAMINA_REGEN * dt)
            if self.tired and self.stamina >= 0.3:
                self.tired = False                 # отдышался — снова можно бежать
        speed = RUN_SPEED if self.running else PLAYER_SPEED

        # Двигаемся сначала по X, проверяем столкновения, потом по Y
        self.x += dx * speed * dt
        self.rect.x = round(self.x)
        for wall in walls:
            if self.rect.colliderect(wall):
                if dx > 0: self.rect.right = wall.left
                if dx < 0: self.rect.left = wall.right
                self.x = self.rect.x

        self.y += dy * speed * dt
        self.rect.y = round(self.y)
        for wall in walls:
            if self.rect.colliderect(wall):
                if dy > 0: self.rect.bottom = wall.top
                if dy < 0: self.rect.top = wall.bottom
                self.y = self.rect.y

        # Шаг звучит 4 раза в секунду — в такт анимации ног
        self.stepped = False
        if self.moving:
            before = int(self.walk_time * 4)
            if self.walk_time == 0:
                self.stepped = True                # первый шаг — сразу
            self.walk_time += dt * (1.6 if self.running else 1)   # на бегу ноги двигаются быстрее
            if int(self.walk_time * 4) != before:
                self.stepped = True
        else:
            self.walk_time = 0.0

    def knockback(self, from_x, from_y, walls):
        """Отбрасывает героя от точки (from_x, from_y) — от монстра, который его ударил."""
        dx = self.rect.centerx - from_x
        dy = self.rect.centery - from_y
        dist = math.hypot(dx, dy) or 1      # "or 1" — чтобы не делить на ноль
        mx = dx / dist * HERO_KNOCKBACK
        my = dy / dist * HERO_KNOCKBACK
        self.x += mx
        self.rect.x = round(self.x)
        for wall in walls:
            if self.rect.colliderect(wall):
                if mx > 0: self.rect.right = wall.left
                elif mx < 0: self.rect.left = wall.right
                self.x = self.rect.x
        self.y += my
        self.rect.y = round(self.y)
        for wall in walls:
            if self.rect.colliderect(wall):
                if my > 0: self.rect.bottom = wall.top
                elif my < 0: self.rect.top = wall.bottom
                self.y = self.rect.y

    def pick_frame(self, frames):
        """Нужный кадр: стоит герой или идёт, и куда смотрит."""
        anim = frames[self.facing]
        if self.moving:
            walk = anim["walk"]
            return walk[int(self.walk_time * 8) % len(walk)]   # 8 кадров в секунду
        return anim["stand"]

    def draw(self, surf, cam_x, cam_y, front=None):
        """front — маска того, что стоит перед героем (нужна для детального героя, см. draw_hero_hd)."""
        self.draw_pos = None
        # После удара монстра герой мигает: через кадр его не рисуем
        if self.hurt > 0 and int(self.hurt * 12) % 2 == 1:
            return
        frame = self.pick_frame(self.frames)

        # Ставим спрайт так, чтобы ноги были внизу хитбокса
        x = self.rect.centerx - HERO_W // 2 - cam_x
        if self.tremble:
            x += random.choice((-1, 0, 0, 1))              # мелкая дрожь
        y = self.rect.bottom - HERO_H - cam_y
        self.draw_pos = (x, y)                             # запоминаем — здесь же нарисуем детального героя

        pygame.draw.ellipse(surf, (35, 35, 40),
                            (self.rect.x - 1 - cam_x, self.rect.bottom - 5 - cam_y, 14, 5))      # тень

        # Предметы в руках: то, что в "дальней" руке, рисуем ДО героя (оно за ним),
        # а то, что в "ближней", — ПОСЛЕ (оно поверх героя)
        behind = HAND_BEHIND[self.facing]
        hands = (("left", self.left_hand), ("right", self.right_hand))
        for hand, item in hands:
            if item and behind[hand]:
                ITEM_DRAWERS[item](surf, self, x, y)
        if not self.hd_frames:                             # детального героя рисуем потом, на большом холсте
            surf.blit(frame, (x, y))
        for hand, item in hands:
            if item and not behind[hand]:
                ITEM_DRAWERS[item](surf, self, x, y)
                if front is not None:                      # предмет в ближней руке — перед героем
                    ITEM_DRAWERS[item](front, self, x, y)


def draw_hero_hd(window, player, game, front, fog_used, clouds):
    """Детальный герой на большом холсте window — поверх уже готовой картинки мира.
    Чтобы он не выглядел "наклейкой", поверх него ещё раз кладём:
      клочья тумана (clouds — функция, которая рисует их на кусочек), туман/темноту (fog_used),
      и то, что стоит ПЕРЕД героем (front — маска: забор, дерево, монстр, предмет в ближней руке)."""
    if not player.hd_frames or getattr(player, "draw_pos", None) is None:
        return
    img = player.pick_frame(player.hd_frames)
    x, y = player.draw_pos
    size = img.get_size()
    pos = (x * ZOOM, y * ZOOM)
    window.blit(img, pos)

    # Силуэт героя: белый, прозрачный там же, где герой. Им "вырезаем" слои точно по фигуре
    silhouette = img.copy()
    silhouette.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)

    def lay_over(part):
        """Кусочек HERO_W x HERO_H из маленькой картинки — увеличить и положить на героя."""
        part = pygame.transform.scale(part, size)
        part.blit(silhouette, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        window.blit(part, pos)

    if clouds:                                         # клочья тумана
        part = pygame.Surface((HERO_W, HERO_H), pygame.SRCALPHA)
        clouds(part, (x, y))
        lay_over(part)
    if fog_used:                                       # туман (или темнота в помещении)
        fog_img, (fx, fy) = fog_used
        part = pygame.Surface((HERO_W, HERO_H), pygame.SRCALPHA)
        part.blit(fog_img, (fx - x, fy - y), special_flags=pygame.BLEND_RGBA_ADD)   # точная копия кусочка
        lay_over(part)

    # Что стоит перед героем — берём из готовой картинки мира, ровно по маске front
    cover = pygame.Surface((HERO_W, HERO_H), pygame.SRCALPHA)
    cover.blit(game, (0, 0), (x, y, HERO_W, HERO_H))
    mask = pygame.Surface((HERO_W, HERO_H), pygame.SRCALPHA)
    mask.blit(front, (0, 0), (x, y, HERO_W, HERO_H), special_flags=pygame.BLEND_RGBA_ADD)
    mask.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
    cover.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    window.blit(pygame.transform.scale(cover, size), pos)


# ---------- МОНСТР ----------
class Monster:
    def __init__(self, pos, frames):
        self.start = pos
        self.frames = frames
        self.rnd = random.Random()
        self.max_hp = MONSTER_HP   # сколько ударов выдерживает (меняется сложностью)
        self.reset()

    def reset(self):
        """Вернуть монстра в начальное состояние (нужно при перезапуске)."""
        self.rect = pygame.Rect(self.start[0], self.start[1], 8, 6)
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)
        self.dir = (0, 0)          # куда бредёт, когда не гонится
        self.think = 0.0           # через сколько секунд выбрать новое направление
        self.chasing = False
        self.moving = False
        self.flip = False          # смотрит влево?
        self.anim = 0.0
        self.twitch = 0            # сколько кадров ещё "дёргается"
        self.hp = self.max_hp      # сколько ударов ещё выдержит
        self.dead = False
        self.corpse_solid = False  # можно ли уже упираться в тело (см. main.py)
        self.stun = 0.0            # сколько секунд ещё оглушён после удара
        self.flash = 0.0           # сколько секунд ещё "вспыхивает" красным после удара

    def move(self, mx, my, walls):
        """Двигает монстра, не пуская в стены. Возвращает True, если упёрся."""
        bumped = False
        self.x += mx
        self.rect.x = round(self.x)
        for wall in walls:
            if self.rect.colliderect(wall):
                if mx > 0: self.rect.right = wall.left
                elif mx < 0: self.rect.left = wall.right
                self.x = self.rect.x
                bumped = True
        self.y += my
        self.rect.y = round(self.y)
        for wall in walls:
            if self.rect.colliderect(wall):
                if my > 0: self.rect.bottom = wall.top
                elif my < 0: self.rect.top = wall.bottom
                self.y = self.rect.y
                bumped = True
        return bumped

    def update(self, dt, player, walls, see_distance):
        """Возвращает расстояние до героя и True, если монстр только что его заметил."""
        if self.dead:
            return 99999, False             # мёртвый монстр никого не замечает и не пугает
        self.flash = max(0.0, self.flash - dt)

        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)           # расстояние по теореме Пифагора

        if self.stun > 0:                   # оглушён ударом — стоит на месте
            self.stun -= dt
            self.moving = False
            return dist, False

        noticed = False
        if not self.chasing and dist < see_distance:
            self.chasing = True
            noticed = True
        elif self.chasing and dist > max(MONSTER_FORGET, see_distance + 30):
            # (теряет из виду всегда дальше, чем замечает — иначе монстр "мигал" бы между погоней и покоем)
            self.chasing = False
            self.think = 0

        if self.chasing and dist > 0:
            # Идём прямо на героя: делим (dx, dy) на длину — получаем направление длиной 1
            vx, vy = dx / dist, dy / dist
            speed = MONSTER_CHASE_SPEED
        else:
            # Бродим: иногда выбираем случайное направление или стоим на месте
            self.think -= dt
            if self.think <= 0:
                self.think = self.rnd.uniform(1.5, 4.0)
                self.dir = self.rnd.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0), (0, 0)])
            vx, vy = self.dir
            speed = MONSTER_WANDER_SPEED

        bumped = self.move(vx * speed * dt, vy * speed * dt, walls)
        if bumped and not self.chasing:
            self.think = 0                  # упёрся в стену — выбираем новое направление

        self.moving = vx != 0 or vy != 0
        if vx > 0.1:
            self.flip = False
        elif vx < -0.1:
            self.flip = True
        self.anim += dt

        if self.twitch > 0:
            self.twitch -= 1
        elif self.rnd.random() < 0.01:      # иногда неестественно дёргается
            self.twitch = 5

        return dist, noticed

    def hit(self, from_x, from_y, walls):
        """Монстра ударили трубой (герой стоял в точке from_x, from_y). Возвращает True, если он погиб."""
        self.hp -= 1
        self.flash = 0.15
        self.stun = STUN_TIME
        self.chasing = True                 # теперь он точно знает, где герой
        # Отлетает назад — в сторону от героя
        dx = self.rect.centerx - from_x
        dy = self.rect.centery - from_y
        dist = math.hypot(dx, dy) or 1      # "or 1" — чтобы не делить на ноль
        self.move(dx / dist * KNOCKBACK, dy / dist * KNOCKBACK, walls)
        if self.hp <= 0:
            self.dead = True
        return self.dead

    def corpse_rect(self):
        """Где лежит тело: его нельзя пройти насквозь (только нижняя часть — как у других предметов)."""
        return pygame.Rect(self.rect.centerx - 9, self.rect.bottom - 7, 18, 7)

    def harmful(self):
        """Может ли монстр сейчас убить героя: живой и не оглушённый."""
        return not self.dead and self.stun <= 0

    def draw(self, surf, cam_x, cam_y):
        if self.dead:                       # лежит на земле
            body = self.frames["corpse"]
            surf.blit(body, (self.rect.centerx - body.get_width() // 2 - cam_x,
                             self.rect.bottom - body.get_height() - cam_y))
            return
        frames = self.frames[self.flip]
        if self.moving:
            speed = 7 if self.chasing else 3                    # в погоне перебирает ногами быстрее
            frame = frames["walk"][int(self.anim * speed) % 2]
        else:
            frame = frames["stand"]
        if self.flash > 0:                  # от удара на мгновение вспыхивает красным
            frame = frame.copy()
            frame.fill((150, 30, 30), special_flags=pygame.BLEND_RGB_ADD)
        jitter = self.rnd.choice((-1, 1)) if self.twitch else 0
        x = self.rect.centerx - MON_W // 2 - cam_x + jitter
        y = self.rect.bottom - MON_H + 1 - cam_y
        pygame.draw.ellipse(surf, (30, 30, 34),
                            (self.rect.x - 2 - cam_x, self.rect.bottom - 3 - cam_y, 12, 5))  # тень
        surf.blit(frame, (x, y))


# ---------- ПРЕДМЕТЫ В РУКАХ ----------
# Какая рука сейчас за героем (True — предмет в ней рисуется ЗА героем, его закрывает тело).
# Смотрит вправо — к нам повёрнут правый бок, левая рука за телом; влево — наоборот;
# стоит лицом к нам — обе руки видно; спиной — обе руки впереди него, за телом.
HAND_BEHIND = {
    "right": {"left": True,  "right": False},
    "left":  {"left": False, "right": True},
    "down":  {"left": False, "right": False},
    "up":    {"left": True,  "right": True},
}

# Фонарик в левой руке: где кулак (точка в картинке героя 12x19). Светит туда, куда смотрит герой.
# Если двигаешь фонарик — поправь и FLASH_ORIGIN в world.py (откуда выходит луч):
# луч = стекло фонарика = кулак + 3 пикселя вперёд; FLASH_ORIGIN = (стекло_x - 6, стекло_y - 16).
FLASHLIGHT_GRIP = {
    "right": (10, 19),
    "left": (6, 19),
    "down": (14, 19),
    "up": (1, 19),
}


# Картинки фонарика в руке: data/items/flashlight_hand_on.png и _off.png.
# Нарисованы так, будто фонарик светит ВПРАВО; для других сторон картинку поворачиваем.
FLASHLIGHT_IMG_GRIP = (2, 2)      # где на картинке кулак
FLASHLIGHT_ANGLES = {"right": 0, "up": 90, "left": 180, "down": 270}   # поворот против часовой


def rotate_point(x, y, w, h, angle):
    """Где окажется пиксель (x, y) картинки размером w x h после поворота на angle градусов."""
    if angle == 90:
        return y, w - 1 - x
    if angle == 180:
        return w - 1 - x, h - 1 - y
    if angle == 270:
        return h - 1 - y, x
    return x, y


def draw_flashlight(surf, player, sx, sy):
    """Рисует фонарик в левой руке. sx, sy — левый верхний угол картинки героя на экране."""
    img = item_image("flashlight_hand_on" if player.light_on else "flashlight_hand_off")
    angle = FLASHLIGHT_ANGLES[player.facing]
    gx, gy = rotate_point(*FLASHLIGHT_IMG_GRIP, img.get_width(), img.get_height(), angle)
    img = pygame.transform.rotate(img, angle)
    hx, hy = FLASHLIGHT_GRIP[player.facing]
    surf.blit(img, (sx + hx - gx, sy + hy - gy))      # ставим так, чтобы кулак попал в руку


# ---------- УДАР ТРУБОЙ ----------
def attack_hitbox(player):
    """Куда достаёт удар: квадрат перед героем, на уровне пояса."""
    dx, dy = FLASH_DIRS[player.facing]
    cx = player.rect.centerx + dx * 12
    cy = player.rect.centery - 8 + dy * 12
    return pygame.Rect(cx - 9, cy - 9, 18, 18)


def monster_body(m):
    """Всё тело монстра (а не только ноги, как у m.rect) — чтобы по нему можно было попасть."""
    return pygame.Rect(m.rect.x - 2, m.rect.bottom - 18, 12, 18)


# Как герой держит трубу, для каждого направления (углы в градусах: 0 — вправо, 90 — вниз,
# -90 — вверх, 180 — влево):
#   "shoulder" — плечо (точка внутри картинки героя 12x19), вокруг него вращается рука
#   "idle"     — угол трубы, когда герой просто держит её (опущена к земле)
#   "wind"     — угол в верхней точке замаха (труба занесена назад)
#   "end"      — угол, где удар заканчивается
PIPE_POSES = {
    "right": {"shoulder": (5, 16), "idle": 55,  "wind": -150, "end": 40},
    "left":  {"shoulder": (11, 16), "idle": 125, "wind": 330,  "end": 140},
    "down":  {"shoulder": (3, 16), "idle": 100, "wind": 240,  "end": 470},
    "up":    {"shoulder": (13, 16), "idle": 80,  "wind": 60,   "end": -130},
}
PIPE_LEN = 12           # длина трубы в пикселях
ARM_LEN = 3             # насколько рука выносит трубу от плеча

# Удар делится на 3 части (доли от SWING_TIME):
WIND_PART = 0.2         # 0 … 0.2   — замах: труба уходит назад
STRIKE_PART = 0.55      # 0.2 … 0.55 — удар: быстрая дуга вперёд (попадание — в середине SWING_TIME)


def ease_out(t):
    """Быстро в начале, плавно в конце."""
    return 1 - (1 - t) ** 2


def lerp_angle(a, b, t):
    """Угол между a и b: при t=0 — a, при t=1 — b."""
    return a + (b - a) * t


def lerp_angle_short(a, b, t):
    """То же, но поворачивает коротким путём (не крутит трубу через лишний круг)."""
    diff = (b - a + 180) % 360 - 180
    return a + diff * t


def pipe_angle(pose, progress):
    """Угол трубы в момент удара. progress: None — просто держит, 0…1 — ход удара."""
    if progress is None:
        return pose["idle"]
    if progress < WIND_PART:                                    # замах назад
        t = ease_out(progress / WIND_PART)
        return lerp_angle(pose["idle"], pose["wind"], t)
    if progress < STRIKE_PART:                                  # удар
        t = (progress - WIND_PART) / (STRIKE_PART - WIND_PART)
        return lerp_angle(pose["wind"], pose["end"], t)
    t = ease_out((progress - STRIKE_PART) / (1 - STRIKE_PART))  # возвращаем трубу вниз
    return lerp_angle_short(pose["end"], pose["idle"], t)


def pipe_line(surf, a, b, color):
    """Ровная пиксельная линия от точки a до точки b (по одному пикселю на шаг)."""
    steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1)
    for i in range(int(steps) + 1):
        t = i / steps
        surf.set_at((round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t)), color)


def draw_pipe(surf, player, sx, sy):
    """Рисует трубу в руке героя. sx, sy — левый верхний угол картинки героя на экране."""
    pose = PIPE_POSES[player.facing]
    angle = math.radians(pipe_angle(pose, player.swing))
    cos, sin = math.cos(angle), math.sin(angle)

    shx, shy = sx + pose["shoulder"][0], sy + pose["shoulder"][1]
    hand = (shx + cos * ARM_LEN, shy + sin * ARM_LEN)               # кисть
    start = (hand[0] - cos * 2, hand[1] - sin * 2)                  # конец трубы за кулаком
    tip = (hand[0] + cos * (PIPE_LEN - 2), hand[1] + sin * (PIPE_LEN - 2))

    # След от удара: светлая дуга, по которой прошёл конец трубы
    p = player.swing
    if p is not None and WIND_PART < p < STRIKE_PART + 0.12:
        now = pipe_angle(pose, p)
        back = pipe_angle(pose, max(WIND_PART, p - 0.15)) if p < STRIKE_PART else pose["wind"]
        if p >= STRIKE_PART:                                    # после удара след быстро гаснет
            fade = (p - STRIKE_PART) / 0.12
            back = lerp_angle(pose["end"], pose["wind"], 0.35 * (1 - fade))
            now = pose["end"]
        r = ARM_LEN + PIPE_LEN - 2
        steps = max(2, int(abs(now - back) / 3))
        for i in range(steps + 1):
            a = math.radians(back + (now - back) * i / steps)
            for rr, col in ((r - 1, (120, 122, 130)), (r, (200, 200, 210))):   # дуга в 2 пикселя
                surf.set_at((round(shx + math.cos(a) * rr), round(shy + math.sin(a) * rr)), col)

    # Рука (рукав куртки) от плеча до кисти — только во время удара
    if p is not None:
        pipe_line(surf, (shx, shy), hand, (82, 88, 76))

    # Сама труба: тёмный контур + светлая середина (металл)
    for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pipe_line(surf, (start[0] + ox, start[1] + oy), (tip[0] + ox, tip[1] + oy), (44, 44, 48))
    pipe_line(surf, start, tip, (88, 88, 94))
    surf.set_at((round(tip[0]), round(tip[1])), (116, 116, 122))   # блик на конце
    surf.set_at((round(hand[0]), round(hand[1])), (206, 188, 172))  # кулак


# Какой функцией рисовать каждый предмет. Новый предмет: напиши для него функцию
# draw_<предмет>(surf, player, sx, sy) и добавь сюда строчку.
ITEM_DRAWERS = {
    "flashlight": draw_flashlight,
    "pipe": draw_pipe,
}


# ---------- КАК ГЕРОЙ ВИДИТ МОНСТРА ----------
def monster_in_view(m, player, flash_on, fog_full):
    """Видит ли герой монстра: монстр рядом (в чистой зоне тумана или темноты) или в луче фонарика.
    fog_full — как далеко видно в этой локации без фонарика."""
    dx = m.rect.centerx - player.rect.centerx
    dy = m.rect.centery - player.rect.centery
    if math.hypot(dx, dy) < fog_full - 10:
        return True
    if flash_on:
        fx, fy = FLASH_DIRS[player.facing]
        hx, hy = FLASH_ORIGIN[player.facing]
        ox, oy = dx - hx, dy - hy
        return flash_strength(ox * fx + oy * fy, -ox * fy + oy * fx) > 0.2
    return False


def face_towards(player, x, y):
    """Повернуть героя лицом к точке (x, y)."""
    dx = x - player.rect.centerx
    dy = y - player.rect.centery
    if abs(dx) > abs(dy):
        player.facing = "right" if dx > 0 else "left"
    else:
        player.facing = "down" if dy > 0 else "up"

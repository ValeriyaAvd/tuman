# =====================================================
#  characters.py — герой и монстры: загрузка картинок, движение, анимация.
#  Картинки лежат в data/hero.png и data/monster.png.
# =====================================================

import os
import math
import random
import pygame
from settings import *
from world import flash_strength, FLASH_DIRS, item_image

# ---------- КАРТИНКИ ПЕРСОНАЖЕЙ ----------
# hero.png — лист кадров героя: 24x38 пикселей, логический размер 12x19.
#   1-я строка — идёт вниз, 2-я — вверх, 3-я — вправо (влево — это зеркальное "вправо").
#   В каждой строке 5 кадров: 1-й — стоит, остальные 4 — шаги по очереди.
# hero_attack.png — удар трубой: 64x58 пикселей на кадр, строки вниз/вверх/вправо/влево, по 4 кадра
#   (замах, удар, доводка, рука опускается). Герой стоит в кадре со сдвигом ATTACK_PAD.
# monster.png — 2 кадра монстра 24x40 (логический размер 12x20).
HERO_W, HERO_H = 12, 19
MON_W, MON_H = 12, 20
ATTACK_W, ATTACK_H = 32, 29
ATTACK_PAD = (10, 6)          # где в кадре удара левый верхний угол обычной картинки героя


def load_image(name):
    """Загружает картинку из папки data (с прозрачностью)."""
    return pygame.image.load(os.path.join(DATA_DIR, name)).convert_alpha()


def cut_frames(sheet, w, h):
    """Режет лист на кадры размером w x h. Возвращает список строк, в каждой — список кадров."""
    w, h = w * ART_SCALE, h * ART_SCALE
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
    attack = cut_frames(load_image("hero_attack.png"), ATTACK_W, ATTACK_H)
    # Влево — своя строка: труба в правой руке, а она у смотрящего влево героя дальняя
    for direction, row in zip(("down", "up", "right", "left"), attack):
        frames[direction]["attack"] = row
    for direction, animation in frames.items():
        stand = animation['stand']
        raised = stand.copy()
        raised.fill((0, 0, 0, 0))
        # Feet stay planted; the upper body breathes by one native pixel.
        split = 26
        raised.blit(stand, (0, split), (0, split, stand.get_width(), stand.get_height() - split))
        raised.blit(stand, (0, -1), (0, 0, stand.get_width(), split + 2))
        animation['idle'] = [stand, raised]
    return frames


def build_monster_frames():
    """Кадры монстра: для взгляда вправо (False) и влево (True — зеркально)."""
    stand, step = cut_frames(load_image("monster.png"), MON_W, MON_H)[0][:2]
    flip = lambda img: pygame.transform.flip(img, True, False)
    corpse = pygame.transform.rotate(stand, 90)                       # убитый монстр лежит на боку
    corpse.fill((45, 45, 45), special_flags=pygame.BLEND_RGB_SUB)     # и выглядит темнее
    return {
        False: {"stand": stand, "walk": [step, stand]},
        True: {"stand": flip(stand), "walk": [flip(step), flip(stand)]},
        "corpse": corpse,
    }


# ---------- ГЕРОЙ ----------
class Player:
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
        self.visual_time = 0.0
        self.render_jitter = 0
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
        self.visual_time += dt
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

    def draw(self, surf, cam_x, cam_y):
        # После удара монстра герой мигает: через кадр его не рисуем
        if self.hurt > 0 and int(self.hurt * 12) % 2 == 1:
            return

        # Выбираем нужный кадр: стоит герой или идёт, и куда смотрит
        anim = self.frames[self.facing]
        attacking = self.right_hand == "pipe" and self.swing is not None
        if attacking:
            frame = anim["attack"][attack_frame(self.swing)]
        elif self.moving:
            walk = anim["walk"]
            frame = walk[int(self.walk_time * 8) % len(walk)]   # 8 кадров в секунду
        else:
            frame = anim['idle'][self.idle_phase()]

        # Ставим спрайт так, чтобы ноги были внизу хитбокса
        x = self.rect.centerx - HERO_W // 2 - cam_x
        self.render_jitter = random.choice((-1, 0, 0, 1)) if self.tremble else 0
        x += self.render_jitter
        y = self.rect.bottom - HERO_H - cam_y

        surf.ellipse((35, 35, 40),
                            (self.rect.x - cam_x, self.rect.bottom - 5 - cam_y, 12, 5))      # тень

        # Предметы в руках: то, что в "дальней" руке, рисуем ДО героя (оно за ним),
        # а то, что в "ближней", — ПОСЛЕ (оно поверх героя)
        # Во время удара труба и рука уже нарисованы в кадре удара
        hands = (("left", self.left_hand), ("right", None if attacking else self.right_hand))
        for hand, item in hands:
            if item and self.hand_behind(hand):
                ITEM_DRAWERS[item](surf, self, x, y)
        if attacking:
            surf.blit(frame, (x - ATTACK_PAD[0], y - ATTACK_PAD[1]))
        else:
            surf.blit(frame, (x, y))
        for hand, item in hands:
            if item and not self.hand_behind(hand):
                ITEM_DRAWERS[item](surf, self, x, y)

    def hand_behind(self, hand):
        """Рисовать ли предмет в этой руке ЗА героем."""
        return HAND_BEHIND[self.facing][hand]

    def idle_phase(self):
        if self.swing is not None:                     # кадры удара сделаны из кадра "стоит"
            return 0
        return int(not self.moving and math.sin(self.visual_time * 1.9) > .25)

    def hand_anchor(self, hand):
        index = int(self.walk_time * 8) % 4 + 1 if self.moving and self.swing is None else 0
        direction = 'right' if self.facing == 'left' else self.facing
        if self.facing == 'left':           # в отражённой картинке руки меняются местами
            hand = 'right' if hand == 'left' else 'left'
        x, y = HAND_ANCHORS[direction][hand][index]
        if self.facing == 'left':
            x = HERO_W * ART_SCALE - 1 - x
        return x / ART_SCALE, (y - self.idle_phase() * int(y < 27)) / ART_SCALE

    def flashlight_origin(self):
        hx, hy = self.hand_anchor('left')
        gx, gy = flashlight_point(FLASHLIGHT_GRIP, self.facing)
        tx, ty = flashlight_point(FLASHLIGHT_TIP, self.facing)
        return (self.rect.centerx - HERO_W / 2 + self.render_jitter + hx + (tx - gx) / ART_SCALE,
                self.rect.bottom - HERO_H + hy + (ty - gy) / ART_SCALE)


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

    def harmful(self):
        """Может ли монстр сейчас убить героя: живой и не оглушённый."""
        return not self.dead and self.stun <= 0

    def draw(self, surf, cam_x, cam_y):
        if self.dead:                       # лежит на земле
            body = self.frames["corpse"]
            surf.blit(body, (self.rect.centerx - body.get_width() / (2 * ART_SCALE) - cam_x,
                             self.rect.bottom - body.get_height() / ART_SCALE - cam_y))
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
        surf.ellipse((30, 30, 34),
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

# Native-pixel fist positions, authored against each frame of the new 24x38 sheet.
# Indices: standing, then the four walking frames. Left-facing poses mirror right.
HAND_ANCHORS = {
    'down': {'left': [(19, 28), (19, 26), (19, 27), (18, 26), (19, 27)],
             'right': [(4, 28), (5, 26), (4, 27), (4, 26), (4, 26)]},
    'up': {'left': [(4, 28), (4, 27), (4, 27), (4, 27), (5, 27)],
           'right': [(19, 28), (19, 27), (19, 27), (19, 27), (19, 26)]},
    'right': {'left': [(11, 27), (8, 26), (6, 26), (17, 27), (17, 26)],
              'right': [(7, 28), (12, 27), (14, 27), (6, 28), (10, 28)]},
}

# Картинки фонарика в руке: data/items/flashlight_hand_on.png и _off.png (9x5 пикселей).
# Нарисованы так, будто фонарик светит ВПРАВО; для "вверх" и "вниз" картинку поворачиваем,
# для "влево" — отражаем (чтобы блик остался сверху).
FLASHLIGHT_ANGLES = {"right": 0, "up": 90, "left": 180, "down": 270}   # поворот против часовой
FLASHLIGHT_SIZE = (9, 5)
FLASHLIGHT_GRIP = (1, 2)    # пиксель картинки, за который держит кулак (задний конец ручки)
FLASHLIGHT_TIP = (8, 2)     # стекло — отсюда идёт луч


def rotate_point(x, y, w, h, angle):
    """Где окажется пиксель (x, y) картинки размером w x h после поворота на angle градусов."""
    if angle == 90:
        return y, w - 1 - x
    if angle == 180:
        return w - 1 - x, h - 1 - y
    if angle == 270:
        return h - 1 - y, x
    return x, y


def flashlight_point(point, facing):
    """Где окажется пиксель картинки фонарика, когда герой смотрит в сторону facing."""
    w, h = FLASHLIGHT_SIZE
    if facing == "left":
        return w - 1 - point[0], point[1]
    return rotate_point(*point, w, h, FLASHLIGHT_ANGLES[facing])


def draw_flashlight(surf, player, sx, sy):
    """Рисует фонарик в левой руке. sx, sy — левый верхний угол картинки героя на экране."""
    img = item_image("flashlight_hand_on" if player.light_on else "flashlight_hand_off")
    gx, gy = flashlight_point(FLASHLIGHT_GRIP, player.facing)
    if player.facing == "left":
        img = pygame.transform.flip(img, True, False)
    else:
        img = pygame.transform.rotate(img, FLASHLIGHT_ANGLES[player.facing])
    hx, hy = player.hand_anchor('left')
    surf.blit(img, (sx + hx - gx / ART_SCALE, sy + hy - gy / ART_SCALE))
    surf.fill((192, 157, 122), (sx + hx, sy + hy, .5, .5))

# ---------- УДАР ТРУБОЙ ----------
def attack_hitbox(player):
    """Куда достаёт удар: квадрат перед героем, на уровне пояса."""
    dx, dy = FLASH_DIRS[player.facing]
    cx = player.rect.centerx + dx * 12
    cy = player.rect.centery - 6 + dy * 12
    return pygame.Rect(cx - 9, cy - 9, 18, 18)


def monster_body(m):
    """Всё тело монстра (а не только ноги, как у m.rect) — чтобы по нему можно было попасть."""
    return pygame.Rect(m.rect.x - 2, m.rect.bottom - 18, 12, 18)


# Труба в руке, пока герой не бьёт: data/items/pipe_hand.png (12x12 пикселей).
# Нарисована наискосок концом вниз-вправо; когда рука героя слева на экране
# (смотрит вниз или влево) — отражаем. PIPE_GRIP — пиксель, за который держит кулак.
PIPE_GRIP = (2, 2)
PIPE_SIZE = (12, 12)

# Кадры удара по ходу замаха (0…1): замах, удар (попадание — в середине), доводка, рука вниз
ATTACK_STEPS = (0.3, 0.55, 0.8)


def attack_frame(progress):
    """Номер кадра удара для хода замаха progress (0…1)."""
    return sum(progress >= step for step in ATTACK_STEPS)


def draw_pipe(surf, player, sx, sy):
    """Рисует трубу в правой руке. sx, sy — левый верхний угол картинки героя на экране."""
    img = item_image("pipe_hand")
    gx, gy = PIPE_GRIP
    if player.facing in ("down", "left"):
        img = pygame.transform.flip(img, True, False)
        gx = PIPE_SIZE[0] - 1 - gx
    hx, hy = player.hand_anchor('right')
    surf.blit(img, (sx + hx - gx / ART_SCALE, sy + hy - gy / ART_SCALE))


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
        hx, hy = player.flashlight_origin()
        ox, oy = m.rect.centerx - hx, m.rect.centery - hy
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

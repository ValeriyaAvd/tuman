# =====================================================
#  story.py — вступление и осмотр окружения
#  (что герой говорит, когда подходит к предметам или осматривает их).
# =====================================================

import pygame
from settings import *
from texts import *
from world import find_groups
from ui import draw_text

# ---------- ВСТУПЛЕНИЕ ----------
class Intro:
    """Вступление в две части:
    "text"  — мысли героя по одной строке на чёрном экране, слышен мотор;
    "scene" — экран светлеет: машина с включёнными фарами, мотор кашляет и глохнет,
              фары гаснут, герой выходит;
    "done"  — вступление закончилось, играем."""

    def __init__(self):
        self.phase = "text"
        self.t = 0.0                    # сколько секунд идёт текущая часть
        self.fired = set()              # номера событий сцены, которые уже произошли
        n = len(INTRO_LINES)
        self.text_length = 1.0 + n * INTRO_LINE_TIME + 1.5 + 1.5   # строки + пауза + затухание

    def update(self, dt):
        """Двигает время вперёд. Возвращает список событий, которые случились в этом кадре."""
        self.t += dt
        events = []
        if self.phase == "text" and self.t >= self.text_length:
            self.phase = "scene"
            self.t = 0.0
        elif self.phase == "scene":
            for index, (when, name) in enumerate(INTRO_SCENE):
                if self.t >= when and index not in self.fired:
                    self.fired.add(index)
                    events.append(name)
                    if name == "control":
                        self.phase = "done"
        return events

    # В звуке car_stall мотор кашляет и примерно через столько секунд глохнет совсем
    ENGINE_DIES = 1.3

    def stall_time(self):
        """Сколько секунд прошло с начала звука "мотор глохнет" (None — ещё не начался)."""
        if self.phase != "scene":
            return None
        for when, name in INTRO_SCENE:
            if name == "stall" and self.t >= when:
                return self.t - when
        return None

    def engine_level(self):
        if self.phase == "text":
            return 0.6 * min(1.0, self.t / 2)   # из салона мотор слышно глуше
        if self.phase == "scene":
            level = 0.6 + 0.4 * min(1.0, self.t / 2)
            s = self.stall_time()
            if s is not None:
                level *= max(0.0, 1 - s / 0.25)   # ровный гул быстро стихает — дальше звучит запись
            return level
        return 0.0

    def headlights_on(self):
        if self.phase != "scene":
            return False
        s = self.stall_time()
        if s is None:
            return True                          # мотор работает — фары горят
        if s < self.ENGINE_DIES:
            return int(s * 7) % 3 != 2           # мотор кашляет — фары мигают
        return self.ENGINE_DIES + 0.12 <= s < self.ENGINE_DIES + 0.2   # мигнули последний раз и погасли

    def black_alpha(self):
        """Насколько экран затемнён (255 — полностью чёрный)."""
        if self.phase == "text":
            return 255
        if self.phase == "scene":
            return int(255 * max(0.0, 1 - self.t / 2))   # за 2 секунды плавно светлеет
        return 0

    def draw_text(self, window, font, small_font):
        """Строки появляются одна за другой, а в конце все вместе гаснут."""
        window.fill((0, 0, 0))
        fade_out = 1 - max(0.0, (self.t - (self.text_length - 1.5)) / 1.5)
        line_h = 44
        top = WIN_H // 2 - len(INTRO_LINES) * line_h // 2
        for i, line in enumerate(INTRO_LINES):
            appear = 1.0 + i * INTRO_LINE_TIME
            alpha = max(0.0, min(1.0, (self.t - appear) / 1.0)) * fade_out
            if alpha > 0:
                draw_text(window, font, line, (WIN_W // 2, top + i * line_h),
                          color=(200, 196, 188), alpha=int(255 * alpha), center=True)
        if self.t > 1.0:
            draw_text(window, small_font, "[Пробел] — пропустить", (WIN_W - 130, WIN_H - 28),
                      color=(90, 90, 95), alpha=int(255 * fade_out), center=True)


# ---------- ОСМОТР ОКРУЖЕНИЯ ----------
class Spot:
    """Место, рядом с которым герой может что-то сказать или осмотреть.
    zone — где нужно стоять, чтобы осмотреть (кнопка E);
    вокруг неё зона побольше — там герой сам скажет фразу "approach" при первом подходе."""

    def __init__(self, kind, zone, texts):
        self.kind = kind
        self.zone = zone
        self.approach_zone = zone.inflate(24, 24)
        self.approach = texts.get("approach")
        self.inspect = texts.get("inspect", [])
        self.approach_said = self.approach is None   # если фразы нет — считаем, что уже сказал
        self.times = 0                               # сколько раз уже осматривали

    def next_text(self):
        text = self.inspect[min(self.times, len(self.inspect) - 1)]
        self.times += 1
        self.approach_said = True                    # осмотрел сам — подходить "заново" незачем
        return text


def build_spots(rows):
    """Находит на карте всё, что можно осмотреть, и создаёт для этого Spot."""
    spots = []

    def texts_for(kind, index):
        t = SPOT_TEXTS[kind]
        return t[index % len(t)] if isinstance(t, list) else t   # у домов и машин — список

    for i, r in enumerate(find_groups(rows, "H")):
        # стоять нужно у двери: она посередине нижней стены
        spots.append(Spot("house", pygame.Rect(r.centerx - 12, r.bottom - 2, 24, 16), texts_for("house", i)))
    for i, r in enumerate(find_groups(rows, "K")):
        spots.append(Spot("shop", pygame.Rect(r.centerx - 16, r.bottom - 2, 32, 16), texts_for("shop", i)))
    for i, r in enumerate(find_groups(rows, "B")):
        spots.append(Spot("bus_stop", r.inflate(16, 28), texts_for("bus_stop", i)))
    for i, r in enumerate(find_groups(rows, "F")):
        spots.append(Spot("booth", r.inflate(20, 20), texts_for("booth", i)))
    for i, r in enumerate(find_groups(rows, "c")):
        spots.append(Spot("wreck", r.inflate(16, 16), texts_for("wreck", i)))
    for i, r in enumerate(find_groups(rows, "A")):
        spots.append(Spot("abyss", r.inflate(24, 24), texts_for("abyss", i)))
    for i, r in enumerate(find_groups(rows, "X")):
        spots.append(Spot("bin", r.inflate(16, 16), texts_for("bin", i)))
    for i, r in enumerate(find_groups(rows, "O")):
        spots.append(Spot("manhole", r.inflate(8, 8), texts_for("manhole", i)))
    for i, r in enumerate(find_groups(rows, "l")):
        spots.append(Spot("broken_lamp", r.inflate(18, 18), texts_for("broken_lamp", i)))
    for i, r in enumerate(find_groups(rows, "C")):
        spots.append(Spot("my_car", r.inflate(20, 20), texts_for("my_car", i)))
    for i, r in enumerate(find_groups(rows, "S")):
        spots.append(Spot("shelf", r.inflate(16, 16), texts_for("shelf", i)))
    for i, r in enumerate(find_groups(rows, "R")):
        spots.append(Spot("counter", r.inflate(16, 16), texts_for("counter", i)))
    for i, r in enumerate(find_groups(rows, "Q")):
        spots.append(Spot("fridge", r.inflate(8, 24), texts_for("fridge", i)))
    for i, r in enumerate(find_groups(rows, "G")):
        # дверь на стене — стоять нужно под ней, на полу
        spots.append(Spot("back_door", pygame.Rect(r.x - 4, r.bottom, r.w + 8, 14), texts_for("back_door", i)))
    return spots


def build_remarks(location_name):
    """Зоны из REMARKS для одной локации: [прямоугольник, фраза, уже сказал?]"""
    return [[pygame.Rect(x * TILE, y * TILE, w * TILE, h * TILE), text, False]
            for x, y, w, h, text in REMARKS.get(location_name, [])]

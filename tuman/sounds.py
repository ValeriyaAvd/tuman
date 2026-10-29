# =====================================================
#  sounds.py — звуки и музыка игры.
#  Все звуки лежат файлами в папке data/sounds (.wav или .ogg).
#  Чтобы заменить звук — положи свой файл с тем же именем вместо старого.
#  Если какого-то файла нет, игра не сломается: этот звук просто будет тишиной.
# =====================================================

import os
import glob
import math
import random
import pygame
from settings import *

SOUND_DIR = os.path.join(DATA_DIR, "sounds")
SOUND_EXTENSIONS = (".wav", ".ogg")


class SoundSystem:
    """Отвечает за все звуки игры. Если звука нет (например, нет колонок),
    игра всё равно работает — просто молча."""

    def __init__(self):
        self.on = False
        try:
            init = pygame.mixer.get_init()
        except pygame.error:
            init = None
        if not SOUND_ON or not init:
            print("Звук выключен или недоступен — игра будет без звука.")
            return
        self.on = True

        # Звуки, у которых несколько вариантов: step_hard_1.wav, step_hard_2.wav, ...
        # Можно добавить сколько угодно своих вариантов — игра подхватит все файлы.
        self.steps = {
            "hard": self.load_group("step_hard"),     # асфальт и плитка
            "soft": self.load_group("step_soft"),     # трава
            "water": self.load_group("step_water"),   # лужи
        }
        # далёкие звуки в тумане: far_*.wav (колокол отдельно — он звучит чаще остальных)
        self.far_sounds = self.load_group("far", skip=("far_bell",))
        self.snd_bell = self.load("far_bell")

        # Звуки по одному
        self.click = self.load("lamp_click")          # треск мигающего фонаря
        self.snd_switch = self.load("flashlight_click")
        self.paper = self.load("note_paper")
        self.snd_growl = self.load("monster_growl")
        self.snd_sting = self.load("death")
        self.snd_shock = self.load("monster_shock")   # первая встреча с монстром
        self.snd_heart = self.load("heartbeat")
        self.snd_pickup = self.load("weapon_pickup")
        self.snd_swing = self.load("weapon_swing")
        self.snd_hit = self.load("weapon_hit")
        self.snd_kill = self.load("monster_death")
        self.car_sounds = {
            "sputter": self.load("car_sputter"),
            "stall": self.load("car_stall"),
            "door_open": self.load("car_door_open"),
            "door_slam": self.load("car_door_slam"),
        }

        # Звуки, которые играют по кругу всю игру (у каждого свой "канал")
        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(6)               # каналы 0–5 заняты под эти звуки
        self.start_loop(0, "wind", VOL_WIND)
        self.ch_buzz = self.start_loop(1, "lamp_buzz", 0)
        self.ch_broken = self.start_loop(2, "lamp_buzz", 0)
        self.ch_static = self.start_loop(3, "radio_static", 0)
        self.ch_music = self.start_loop(4, "music", 0) if VOL_MUSIC > 0 else pygame.mixer.Channel(4)
        self.ch_engine = self.start_loop(5, "car_engine", 0)

        self.music_vol = 0.0
        self.far_timer = random.uniform(8, 15)     # когда прозвучит первый далёкий звук
        self.bell_timer = random.uniform(5, 12)    # когда первый раз ударит колокол
        self.last_step = None

    # ---------- загрузка ----------
    def load(self, name):
        """Загружает data/sounds/<name>.wav (или .ogg). Если файла нет — возвращает None."""
        for ext in SOUND_EXTENSIONS:
            path = os.path.join(SOUND_DIR, name + ext)
            if os.path.exists(path):
                try:
                    return pygame.mixer.Sound(path)
                except pygame.error as e:
                    print(f"Не получилось загрузить звук {name + ext}: {e}")
                    return None
        print(f"Нет звука {name} (.wav или .ogg) в папке data/sounds — будет тишина.")
        return None

    def load_group(self, prefix, skip=()):
        """Загружает все файлы, которые начинаются на <prefix>_ (например, far_bell.wav, far_clang.wav)."""
        files = []
        for ext in SOUND_EXTENSIONS:
            files += glob.glob(os.path.join(SOUND_DIR, prefix + "_*" + ext))
        sounds = []
        for path in sorted(files):
            if os.path.splitext(os.path.basename(path))[0] in skip:
                continue
            try:
                sounds.append(pygame.mixer.Sound(path))
            except pygame.error as e:
                print(f"Не получилось загрузить звук {os.path.basename(path)}: {e}")
        if not sounds:
            print(f"Нет звуков {prefix}_*.wav в папке data/sounds — будет тишина.")
        return sounds

    def start_loop(self, channel_number, name, volume):
        """Запускает звук по кругу на своём канале (loops=-1 — играть бесконечно)."""
        ch = pygame.mixer.Channel(channel_number)
        sound = self.load(name)
        if sound:
            ch.play(sound, loops=-1)
        ch.set_volume(volume)
        return ch

    # ---------- проигрывание ----------
    def play(self, sound, volume, pan=0.0):
        """pan: -1 — только левое ухо, 0 — по центру, 1 — только правое."""
        if not self.on or sound is None:
            return
        ch = sound.play()
        if ch:
            ch.set_volume(volume * min(1.0, 1 - pan), volume * min(1.0, 1 + pan))

    def footstep(self, ground):
        if not self.on or not self.steps[ground]:
            return
        options = self.steps[ground]
        sound = random.choice([s for s in options if s is not self.last_step] or options)
        self.last_step = sound                     # чтобы два одинаковых шага не шли подряд
        self.play(sound, VOL_STEPS * random.uniform(0.8, 1.0))

    def note(self):
        self.play(self.paper, VOL_NOTE)

    def switch(self):
        self.play(self.snd_switch, VOL_STEPS * 1.5)

    def growl(self, pan):
        self.play(self.snd_growl, VOL_SCARE * 0.7, pan)

    def shock(self):
        self.play(self.snd_shock, VOL_SCARE * 0.6)

    def heartbeat(self, volume):
        self.play(self.snd_heart, VOL_HEART * volume)

    def scare(self):
        self.play(self.snd_sting, VOL_SCARE)

    def pickup(self):
        self.play(self.snd_pickup, VOL_WEAPON)

    def swing(self):
        self.play(self.snd_swing, VOL_WEAPON * random.uniform(0.8, 1.0))

    def hit(self):
        self.play(self.snd_hit, VOL_WEAPON)

    def monster_death(self):
        self.play(self.snd_kill, VOL_SCARE * 0.8)

    def car(self, name):
        """Звуки вступления: "sputter", "stall", "door_open", "door_slam"."""
        self.play(self.car_sounds[name], VOL_CAR)

    # ---------- громкость звуков, которые играют по кругу ----------
    def radio(self, level):
        """level от 0 (монстров рядом нет) до 1 (монстр вплотную)."""
        if self.on:
            self.ch_static.set_volume(VOL_RADIO * level * random.uniform(0.75, 1.0))

    def engine(self, level):
        """Громкость мотора: 0 — тихо, 1 — полная."""
        if self.on:
            self.ch_engine.set_volume(VOL_CAR * level)

    def engine_off(self):
        if self.on:
            self.ch_engine.stop()

    def music(self, dt, radio, dead):
        """Мелодия плавно затихает, когда рядом монстр (чтобы было слышно радио),
        и пропадает после смерти."""
        if not self.on or VOL_MUSIC <= 0:
            return
        target = 0.0 if dead else VOL_MUSIC * (1 - 0.75 * radio)
        self.music_vol += (target - self.music_vol) * min(1.0, dt * 1.5)   # плавно, без скачков
        self.ch_music.set_volume(self.music_vol)

    def update(self, dt, px, py, glows, broken_on, broken_switched_on):
        """Вызывается каждый кадр: громкость жужжания зависит от расстояния до фонарей,
        а иногда издалека доносится странный звук."""
        if not self.on:
            return

        def nearest(kinds):
            best = None
            for kind, gx, gy in glows:
                if kind in kinds:
                    d = math.hypot(gx - px, gy - py)
                    if best is None or d < best[0]:
                        best = (d, gx - px)
            return best

        def set_by_distance(ch, found, radius, volume):
            if found is None or found[0] > radius:
                ch.set_volume(0)
                return 0.0
            v = volume * (1 - found[0] / radius) ** 2
            pan = max(-1.0, min(1.0, found[1] / radius))
            ch.set_volume(v * min(1.0, 1 - pan), v * min(1.0, 1 + pan))
            return v

        set_by_distance(self.ch_buzz, nearest(("lamp",)), 70, VOL_BUZZ)
        broken = nearest(("lamp_broken", "desk"))
        set_by_distance(self.ch_broken, broken, 90, VOL_BUZZ * 1.4 if broken_on else 0)
        if broken_switched_on and broken and broken[0] < 90:
            self.play(self.click, VOL_BUZZ * 2 * (1 - broken[0] / 90))

        self.far_timer -= dt
        if self.far_timer <= 0:
            self.far_timer = random.uniform(15, 40)
            if self.far_sounds:
                self.play(random.choice(self.far_sounds), VOL_FAR * random.uniform(0.5, 1.0),
                          pan=random.uniform(-0.9, 0.9))

        # Колокол: примерно раз в 20–40 секунд, громкость и сторона каждый раз разные
        self.bell_timer -= dt
        if self.bell_timer <= 0:
            self.bell_timer = random.uniform(20, 40)
            self.play(self.snd_bell, VOL_FAR * random.uniform(0.5, 1.0),
                      pan=random.uniform(-0.9, 0.9))

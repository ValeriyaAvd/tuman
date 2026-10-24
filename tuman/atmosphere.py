"""Independent lamp faults, anchored canopy motion and proximity-driven tape damage."""
import math
import random
import pygame
from settings import ART_SCALE


class Lamp:
    def __init__(self, kind, x, y):
        self.kind, self.x, self.y = kind, x, y
        self.random = random.Random(f'{kind}:{x:.3f}:{y:.3f}')
        self.wait = self.random.uniform(1, 8) if kind == 'lamp_broken' else self.random.uniform(4, 22)
        self.burst = self.pulse = 0.0
        self.level = 1.0

    def update(self, dt):
        previous = self.level
        if self.burst > 0:
            self.burst -= dt
            self.pulse -= dt
            if self.pulse <= 0:
                self.level = self.random.choice((0, .08, .25, .8, 1, 1))
                self.pulse = self.random.uniform(.035, .15)
            if self.burst <= 0:
                self.level = 1.0
                self.wait = self.random.uniform(1.5, 6) if self.kind == 'lamp_broken' else self.random.uniform(10, 30)
        else:
            self.wait -= dt
            if self.wait <= 0:
                self.burst = self.random.uniform(.6, 2.8)
                self.pulse = 0
        return previous < .3 <= self.level


class LampBank:
    def __init__(self, glows):
        self.lamps = [Lamp(*g) for g in glows if g[0] in ('lamp', 'lamp_broken')]

    def update(self, dt):
        switched = False
        for lamp in self.lamps:
            turned_on = lamp.update(dt)
            switched = (turned_on and lamp.kind == 'lamp_broken') or switched
        return any(l.level > .3 for l in self.lamps if l.kind == 'lamp_broken'), switched

    def level_at(self, kind, x, y):
        candidates = [lamp for lamp in self.lamps if lamp.kind == kind]
        if not candidates:
            return 1.0
        lamp = min(candidates, key=lambda l: (l.x - x) ** 2 + (l.y - y) ** 2)
        return lamp.level if math.hypot(lamp.x - x, lamp.y - y) < 16 else 1.0


def foliage_frame(image, phase, kind='tree'):
    """Slow common wind plus delayed branch motion; roots never move."""
    frame = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    w, h = image.get_size()
    root = round(h * (.76 if kind == 'tree' else .86))
    amplitude = 2.1 if kind == 'tree' else 1.1
    bend = math.sin(phase) * amplitude + math.sin(phase * 2) * amplitude * .4
    segment = max(6, w // 4)
    for y in range(h):
        if y >= root:
            frame.blit(image, (0, y), (0, y, w, 1))
            continue
        weight = max(0, 1 - y / max(1, root))
        for x in range(0, w, segment):
            branch = math.sin(phase * 3 + x * .13 + y * .06) * .75 * weight
            dx = round(bend * weight ** 1.5 + branch)
            frame.blit(image, (x + dx, y), (x, y, min(segment + 1, w - x), 1))
    return frame


def fire_frame(image, phase):
    frame = image.copy()
    w, h = image.get_size()
    flame_h = round(h * .55)
    frame.fill((0, 0, 0, 0), (0, 0, w, flame_h))
    for y in range(flame_h):
        offset = round(math.sin(phase * .9 + y * .4) * 1.7 * (1 - y / flame_h))
        frame.blit(image, (offset, y), (0, y, w, 1))
    for i in range(3):
        y = round((phase * 4 + i * 9) % max(1, flame_h))
        x = round(w / 2 + math.sin(phase + i) * (w / 4))
        frame.set_at((min(w - 1, max(0, x)), y), (221, 135, 56, 180))
    return frame


class SceneryAnimator:
    def __init__(self, props, effects, lamps):
        self.props, self.effects, self.lamps = props, effects, lamps
        self.cache = {}

    def props_at(self, time):
        result = []
        for i, (z, image, x, y) in enumerate(self.props):
            effect = self.effects.get(i, '')
            if effect in ('tree', 'bush', 'grass', 'reeds'):
                # Nearby plants share the gust, with a spatial delay along the street.
                phase = time * .95 + x * .021 + y * .012
                step = round(phase / (math.pi * 2) * 48) % 48
                key = id(image), effect, step
                if key not in self.cache:
                    self.cache[key] = foliage_frame(image, step * math.pi * 2 / 48, effect)
                image = self.cache[key]
            elif effect == 'fire':
                step = round(time * 12 + x * .1) % 12
                key = id(image), 'fire', step
                if key not in self.cache:
                    self.cache[key] = fire_frame(image, step)
                image = self.cache[key]
            elif effect in ('paper', 'cloth'):
                step = round((math.sin(time * 1.8 + x * .07) + 1) * 2)
                key = id(image), effect, step
                if key not in self.cache:
                    frame = image.copy()
                    # Lift one loose corner; most of the paper stays against the ground.
                    corner = pygame.Rect(image.get_width() // 2, 0, image.get_width() // 2, image.get_height() // 2)
                    frame.fill((0, 0, 0, 0), corner)
                    frame.blit(image, (corner.x, corner.y - (step % 2)), corner)
                    self.cache[key] = frame
                image = self.cache[key]
            elif effect in ('lamp', 'lamp_broken'):
                level = self.lamps.level_at(effect, x + 9, y + 5)
                step = round(level * 4)
                key = id(image), 'lamp', step
                if key not in self.cache:
                    frame = image.copy()
                    # Change only the glass; the pole and its collision remain fixed.
                    glass = pygame.Rect(7 * ART_SCALE, 6 * ART_SCALE, 4 * ART_SCALE, ART_SCALE)
                    frame.fill((50 + 42 * step, 48 + 38 * step, 39 + 27 * step), glass)
                    self.cache[key] = frame
                image = self.cache[key]
            result.append((z, image, x, y))
        return result


class TapeDistortion:
    def __init__(self, size, seed=None):
        self.size = size
        self.random = random.Random(seed)
        self.time = self.level = 0.0
        self.noise_clock = self.tear_clock = 0.0
        self.grain = pygame.Surface(size, pygame.SRCALPHA)
        self.grain_frames = []
        self.grain_index = 0
        self.scanlines = pygame.Surface(size, pygame.SRCALPHA)
        self.grain.fill((0, 0, 0, 0))
        for y in range(0, size[1], 3):
            self.scanlines.fill((0, 0, 0, 12), (0, y, size[0], 1))
        for _ in range(8):
            frame = pygame.Surface(size, pygame.SRCALPHA)
            for _ in range(int(size[0] * size[1] * .043)):
                value = self.random.randint(40, 165)
                frame.set_at((self.random.randrange(size[0]), self.random.randrange(size[1])),
                             (value, value, value, self.random.randrange(44)))
            self.grain_frames.append(frame)
        self.tear = None

    def apply(self, surface, dt, proximity):
        self.time += dt
        target = min(1.0, max(0, proximity)) ** .7
        self.level += (target - self.level) * min(1, dt * (5 if target > self.level else 2))
        amount = self.level
        if amount < .008:
            return
        w, h = self.size
        self.noise_clock -= dt
        self.tear_clock -= dt
        if self.noise_clock <= 0:
            self.noise_clock = 1 / 18
            self.grain_index = (self.grain_index + self.random.randrange(1, 4)) % len(self.grain_frames)
            self.grain = self.grain_frames[self.grain_index]
        self.grain.set_alpha(round(255 * (.18 + amount * .82)))
        if self.tear_clock <= 0:
            self.tear_clock = self.random.uniform(.12, .65) / (.4 + amount)
            self.tear = (self.random.randrange(h), self.random.randint(2, 5 + round(amount * 14)),
                         self.random.choice((-1, 1)) * round(2 + amount * 10))
        original = surface.copy()
        # Tracking drift affects horizontal tape bands, with no displacement of the UI.
        for y in range(0, h, 6):
            offset = round(math.sin(y * .07 + self.time * 2.8) * amount * 1.8)
            if offset:
                surface.blit(original, (offset, y), (0, y, w, 6))
        if self.tear:
            y, height, offset = self.tear
            surface.blit(original, (offset, y), (0, y, w, height))
        if amount > .18:
            # Restrained red/cyan separation, not a full-screen RGB flash.
            shift = max(1, round(amount * 3))
            red = original.copy()
            red.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
            red.set_alpha(round(amount * 36))
            surface.blit(red, (shift, 0))
            cyan = original.copy()
            cyan.fill((0, 255, 255), special_flags=pygame.BLEND_RGB_MULT)
            cyan.set_alpha(round(amount * 25))
            surface.blit(cyan, (-shift, 0))
        self.scanlines.set_alpha(round(45 + amount * 150))
        surface.blit(self.scanlines, (0, 0))
        surface.blit(self.grain, (0, 0))
        # A slow head-switching band rolls down the tape as the monster closes in.
        y = round((self.time * (13 + amount * 18)) % (h + 42)) - 42
        shade = pygame.Surface((w, 30), pygame.SRCALPHA)
        shade.fill((6, 8, 10, round(amount * 48)))
        surface.blit(shade, (0, y))

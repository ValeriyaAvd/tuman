"""Water responds to footsteps; particles are transient and do not alter map state."""
import math
import random
import pygame
from settings import ART_SCALE


class WaterSystem:
    def __init__(self, puddles):
        self.puddles = puddles
        self.ripples = []
        self.cooldown = 0.0
        self.time = 0.0

    def at(self, position):
        x, y = position
        for rect in self.puddles:
            if ((x - rect.centerx) / max(1, rect.w / 2)) ** 2 + ((y - rect.centery) / max(1, rect.h / 2)) ** 2 < .95:
                return rect
        return None

    def update(self, dt, position, stepped=False):
        self.time += dt
        self.cooldown = max(0, self.cooldown - dt)
        self.ripples = [(x, y, age + dt, rect) for x, y, age, rect in self.ripples if age + dt < .8]
        rect = self.at(position)
        if rect is not None and stepped and self.cooldown <= 0:
            self.ripples.append((*position, 0.0, rect))
            self.cooldown = .12

    def draw(self, canvas, camera):
        cx, cy = camera
        for rect in self.puddles:
            w, h = max(2, rect.w * ART_SCALE), max(2, rect.h * ART_SCALE)
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            # Slow, dim moving reflections, clipped to the water's ellipse.
            phase = math.sin(self.time * .8 + rect.x)
            y = round(h * (.42 + phase * .04))
            pygame.draw.line(overlay, (102, 123, 128, 45), (w // 4, y), (w * 3 // 4, y - 1))
            mask = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(mask, (255, 255, 255, 255), (1, 1, w - 2, h - 2))
            for x, yy, age, owner in self.ripples:
                if owner != rect:
                    continue
                radius = 1 + age * 11
                alpha = round(135 * (1 - age / .8))
                px, py = (x - rect.x) * ART_SCALE, (yy - rect.y) * ART_SCALE
                pygame.draw.ellipse(overlay, (146, 164, 165, alpha),
                                    (round(px - radius * 2), round(py - radius), round(radius * 4), max(2, round(radius * 2))), 1)
                if age < .18:
                    for sign in (-1, 1):
                        pygame.draw.line(overlay, (161, 177, 174, alpha),
                                         (round(px + sign * age * 18), round(py - age * 12)),
                                         (round(px + sign * age * 18), round(py - age * 12 - 2)))
            overlay.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            canvas.blit(overlay, (rect.x - cx, rect.y - cy))


class DriftingLeaves:
    def __init__(self, size, seed=34):
        self.size = size
        rnd = random.Random(seed)
        self.leaves = [(rnd.random() * size[0], rnd.random() * size[1], rnd.uniform(3, 8), rnd.random() * 6.28)
                       for _ in range(11)]
        self.time = 0

    def draw(self, canvas, camera, dt):
        self.time += dt
        w, h = self.size
        for x, y, speed, phase in self.leaves:
            px = (x + self.time * speed - camera[0] * .08) % (w + 12) - 6
            py = (y + self.time * speed * .22 + math.sin(self.time * 1.4 + phase) * 3) % (h + 12) - 6
            angle = math.sin(self.time * 2 + phase)
            canvas.line((93, 77, 49), (px, py), (px + 1 + angle, py + .5), width=.5)

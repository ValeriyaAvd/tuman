"""Native 2x art, with gameplay coordinates independent of texture resolution."""
import pygame
from settings import ART_SCALE, SOFT_BLUR, MOTION_BLUR


def hd_effect(image):
    return pygame.transform.smoothscale(image, (image.get_width() * ART_SCALE,
                                                image.get_height() * ART_SCALE))


def draw_ground_corpses(canvas, monsters, camera, view):
    """Return only living actors for depth sorting; dead bodies stay below all actors."""
    living = []
    for monster in monsters:
        if not view.colliderect(monster.rect):
            continue
        if monster.dead:
            monster.draw(canvas, *camera)
        else:
            living.append((monster.rect.bottom, monster))
    return living


class LensEffects:
    """Slight optical softness and bounded motion trails, before the UI is drawn."""
    def __init__(self, softness=SOFT_BLUR, motion=MOTION_BLUR):
        self.softness, self.motion = softness, motion
        self.previous = self.camera = self.scene = None

    def apply(self, surface, camera, scene, movement, dt):
        raw = surface.copy()
        if self.softness > 0:
            w, h = surface.get_size()
            soft = pygame.transform.smoothscale(surface, (max(1, w // 2), max(1, h // 2)))
            soft = pygame.transform.smoothscale(soft, (w, h))
            soft.set_alpha(round(min(.3, self.softness) * 255))
            surface.blit(soft, (0, 0))
        valid = (self.previous is not None and self.scene == scene and dt <= .1
                 and abs(camera[0] - self.camera[0]) + abs(camera[1] - self.camera[1]) < 32)
        if valid and movement and self.motion > 0:
            previous = self.previous.copy()
            previous.set_alpha(round(min(.25, self.motion * movement) * 255))
            surface.blit(previous, (round((self.camera[0] - camera[0]) * ART_SCALE),
                                    round((self.camera[1] - camera[1]) * ART_SCALE)))
        self.previous, self.camera, self.scene = raw, tuple(camera), scene


class WorldCanvas:
    def __init__(self, size):
        self.surface = pygame.Surface((size[0] * ART_SCALE, size[1] * ART_SCALE))

    def blit(self, image, dest, **kwargs):
        return self.surface.blit(image, (round(dest[0] * ART_SCALE), round(dest[1] * ART_SCALE)), **kwargs)

    def fill(self, color, rect=None):
        if rect is not None:
            rect = pygame.Rect(*(round(v * ART_SCALE) for v in rect))
        return self.surface.fill(color, rect)

    def set_at(self, pos, color):
        # Procedural effects can use fractions of a world pixel at native resolution.
        x, y = round(pos[0] * ART_SCALE), round(pos[1] * ART_SCALE)
        if 0 <= x < self.surface.get_width() and 0 <= y < self.surface.get_height():
            self.surface.set_at((x, y), color)

    def ellipse(self, color, rect):
        pygame.draw.ellipse(self.surface, color, tuple(round(v * ART_SCALE) for v in rect))

    def line(self, color, start, end, width=1):
        pygame.draw.line(self.surface, color, tuple(round(v * ART_SCALE) for v in start),
                         tuple(round(v * ART_SCALE) for v in end), max(1, round(width * ART_SCALE)))

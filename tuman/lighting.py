"""Flashlight visibility in world coordinates; roofs stop rays, facades receive light."""
import math
import pygame
from settings import *
from world import FLASH_DIRS, flash_strength
from rendering import hd_effect


def facade_edges(rect):
    """Front facade accepts light from below, side walls stop grazing rays."""
    return [pygame.Rect(rect.left, rect.top, 1, rect.h),
            pygame.Rect(rect.right - 1, rect.top, 1, rect.h)]


def merge_occluders(rectangles):
    """Exact union of touching rows/columns; preserve gaps and concave corners."""
    rectangles = [pygame.Rect(r) for r in sorted(set(tuple(r) for r in rectangles)) if r[2] > 0 and r[3] > 0]
    rectangles = [r for r in rectangles if not any(other != r and other.contains(r) for other in rectangles)]
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(rectangles):
            for j in range(i + 1, len(rectangles)):
                b = rectangles[j]
                horizontal = a.y == b.y and a.h == b.h and max(a.left, b.left) <= min(a.right, b.right)
                vertical = a.x == b.x and a.w == b.w and max(a.top, b.top) <= min(a.bottom, b.bottom)
                if horizontal or vertical:
                    rectangles[i] = a.union(b)
                    rectangles.pop(j)
                    changed = True
                    break
            if changed:
                break
    return rectangles


def ray_distance(origin, direction, rect, limit):
    near, far = 0.0, limit
    for start, delta, low, high in ((origin[0], direction[0], rect.left, rect.right),
                                   (origin[1], direction[1], rect.top, rect.bottom)):
        if abs(delta) < 1e-9:
            if not low <= start <= high:
                return limit
        else:
            a, b = (low - start) / delta, (high - start) / delta
            near, far = max(near, min(a, b)), min(far, max(a, b))
            if near > far:
                return limit
    return max(0, near) if far >= 0 else limit


def visibility_polygon(origin, facing, blockers):
    center = math.atan2(FLASH_DIRS[facing][1], FLASH_DIRS[facing][0])
    half = math.radians(FLASH_ANGLE + 3)  # include the soft edge near the emitter
    angles = [center - half + 2 * half * i / 64 for i in range(65)]
    nearby = [r for r in blockers if pygame.Rect(origin[0] - FLASH_RANGE, origin[1] - FLASH_RANGE,
                                                  FLASH_RANGE * 2, FLASH_RANGE * 2).colliderect(r)]
    for r in nearby:
        for x, y in (r.topleft, r.topright, r.bottomleft, r.bottomright):
            angle = math.atan2(y - origin[1], x - origin[0])
            offset = (angle - center + math.pi) % (math.pi * 2) - math.pi
            if abs(offset) <= half:
                angles.extend([center + offset - .0001, center + offset, center + offset + .0001])
    points = [origin]
    for angle in sorted(angles):
        direction = math.cos(angle), math.sin(angle)
        distance = min((ray_distance(origin, direction, rect, FLASH_RANGE) for rect in nearby), default=FLASH_RANGE)
        points.append((origin[0] + direction[0] * distance, origin[1] + direction[1] * distance))
    return points, nearby


class FlashlightRenderer:
    def __init__(self, inside, textures):
        self.color = FOG_INSIDE_COLOR if inside else FOG_COLOR
        alpha = FOG_INSIDE_ALPHA if inside else FOG_MAX_ALPHA
        self.textures = textures
        self.cuts = {}
        for name, (dx, dy) in FLASH_DIRS.items():
            cut = pygame.Surface((FLASH_RANGE * 2, FLASH_RANGE * 2), pygame.SRCALPHA)
            cut.fill((*self.color, alpha))
            for y in range(-FLASH_RANGE + 1, FLASH_RANGE):
                for x in range(-FLASH_RANGE + 1, FLASH_RANGE):
                    k = flash_strength(x * dx + y * dy, -x * dy + y * dx)
                    if k:
                        cut.set_at((x + FLASH_RANGE, y + FLASH_RANGE), (*self.color, round(alpha * (1 - k))))
            self.cuts[name] = hd_effect(cut)
        self.cache_key = None

    def masks(self, origin, facing, blockers):
        key = (tuple(round(v * ART_SCALE) for v in origin), facing, tuple(tuple(r) for r in blockers))
        if self.cache_key == key:
            return self.cached
        size = FLASH_RANGE * 2 * ART_SCALE
        visible = pygame.Surface((size, size))
        visible.fill((0, 0, 0))
        shadow = pygame.Surface((size, size), pygame.SRCALPHA)
        shadow.fill((*self.color, 255))
        points, nearby = visibility_polygon(origin, facing, blockers)
        local = [(round((x - origin[0] + FLASH_RANGE) * ART_SCALE),
                  round((y - origin[1] + FLASH_RANGE) * ART_SCALE)) for x, y in points]
        pygame.draw.polygon(visible, (255, 255, 255), local)
        pygame.draw.polygon(shadow, (*self.color, 0), local)
        # Ray endpoints can touch an edge: roofs themselves must never be revealed.
        for r in nearby:
            local_rect = pygame.Rect(round((r.x - origin[0] + FLASH_RANGE) * ART_SCALE),
                                     round((r.y - origin[1] + FLASH_RANGE) * ART_SCALE),
                                     r.w * ART_SCALE, r.h * ART_SCALE)
            visible.fill((0, 0, 0), local_rect)
            shadow.fill((*self.color, 255), local_rect)
        self.cache_key, self.cached = key, (visible, shadow)
        return self.cached

    def draw(self, canvas, fog, origin, center, facing, camera, blockers):
        mask, shadow = self.masks(origin, facing, blockers)
        _, light, beam = self.textures[facing]
        light, beam, cut = light.copy(), beam.copy(), self.cuts[facing].copy()
        light.blit(mask, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        beam.blit(mask, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        cut.blit(shadow, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
        cx, cy = camera
        corner = origin[0] - cx - FLASH_RANGE, origin[1] - cy - FLASH_RANGE
        canvas.blit(light, corner, special_flags=pygame.BLEND_RGB_ADD)
        fog_layer = pygame.Surface(canvas.surface.get_size(), pygame.SRCALPHA)
        fog_layer.blit(fog, (round((center[0] - cx - GAME_W) * ART_SCALE),
                             round((center[1] - cy - GAME_H) * ART_SCALE)))
        fog_layer.blit(cut, (round(corner[0] * ART_SCALE), round(corner[1] * ART_SCALE)),
                       special_flags=pygame.BLEND_RGBA_MIN)
        canvas.surface.blit(fog_layer, (0, 0))
        canvas.blit(beam, corner, special_flags=pygame.BLEND_RGB_ADD)

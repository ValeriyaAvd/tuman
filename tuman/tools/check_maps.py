"""Validate every map, door, spawn and referenced resource without opening a window."""
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from characters import build_monster_frames
from locations import build_locations
from settings import DIFFICULTIES, DEFAULT_DIFFICULTY, TILE
from tiled_map import MapError


def validate(store):
    for name in store:
        loc = store[name]
        for spawn, (x, y) in loc.spawns.items():
            hitbox = pygame.Rect(x - 2, y, 12, 6)
            if not pygame.Rect(0, 0, len(loc.rows[0]) * TILE, len(loc.rows) * TILE).contains(hitbox):
                raise MapError(f'{name}: spawn {spawn} lies outside map bounds')
            if any(hitbox.colliderect(wall) for wall in loc.walls):
                raise MapError(f'{name}: spawn {spawn} intersects a collision')
        for door in loc.doors:
            store.enter(door)
        print(f'{name}: OK ({loc.map_surf.get_width()}x{loc.map_surf.get_height()}, '
              f'{len(loc.doors)} doors, {len(loc.monsters)} monsters)')


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    try:
        validate(build_locations(build_monster_frames(), DIFFICULTIES[DEFAULT_DIFFICULTY]))
    except (MapError, KeyError, OSError, ValueError, pygame.error) as exc:
        print(f'MAP ERROR: {exc}', file=sys.stderr)
        return 1
    finally:
        pygame.quit()
    return 0


if __name__ == '__main__':
    sys.exit(main())

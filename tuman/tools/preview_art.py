"""Render native art with the real game draw functions, without opening a window."""
import os
from pathlib import Path
import sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from characters import Player, build_hero_frames, build_monster_frames
from locations import build_locations
from rendering import WorldCanvas
from settings import DIFFICULTIES


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    store = build_locations(build_monster_frames(), DIFFICULTIES['normal'])
    hero_frames = build_hero_frames()
    preview = pygame.Surface((1280, 420))
    preview.fill((20, 22, 25))
    font = pygame.font.SysFont('arial', 20)
    for i, (name, camera, position) in enumerate([('street', (0, 145), (125, 270)),
                                                 ('shop', (0, 0), (120, 150))]):
        loc = store[name]
        canvas = WorldCanvas((320, 180))
        canvas.fill((8, 8, 10))
        cx, cy = camera
        canvas.blit(loc.map_surf, (-cx, -cy))
        for _, image, x, y in loc.ground_scenery.props_at(0):
            canvas.blit(image, (x-cx, y-cy))
        loc.water.draw(canvas, (cx, cy))
        hero = Player(position, hero_frames)
        hero.left_hand, hero.right_hand, hero.light_on = 'flashlight', 'pipe', True
        hero.facing = 'right'
        hero.swing = .4
        draw = [(z, (img, x, y)) for z, img, x, y in loc.scenery.props_at(0)]
        draw += [(hero.rect.bottom, hero)]
        for monster in loc.monsters:
            draw.append((monster.rect.bottom, monster))
        for _, obj in sorted(draw, key=lambda item: item[0]):
            if isinstance(obj, tuple):
                image, x, y = obj
                canvas.blit(image, (x - cx, y - cy))
            else:
                obj.draw(canvas, cx, cy)
        preview.blit(canvas.surface, (i * 640, 48))
        preview.blit(font.render(f'{name} / native 32px tiles / art preview without fog', True, (210, 210, 200)), (i * 640 + 16, 16))
    output = Path(__file__).resolve().parents[1] / 'art_source/environment-preview.png'
    pygame.image.save(preview, str(output))
    pygame.quit()
    print(output)


if __name__ == '__main__':
    main()

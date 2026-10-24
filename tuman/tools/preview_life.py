"""Visual QA: held equipment/idle GIF and roof-lighting/VHS contact sheet."""
import os
import math
from pathlib import Path
import sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image
from atmosphere import TapeDistortion, foliage_frame
from characters import Player, build_hero_frames, build_monster_frames
from locations import build_locations
from rendering import WorldCanvas
from settings import DIFFICULTIES, GAME_W, GAME_H, ART_SCALE

ROOT = Path(__file__).resolve().parents[1]


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    frames = build_hero_frames()
    store = build_locations(build_monster_frames(), DIFFICULTIES['normal'])
    street = store['street']
    actors = [Player((28 + i * 36, 65), frames) for i in range(4)]
    for player, direction in zip(actors, ('down', 'up', 'right', 'left')):
        player.facing, player.left_hand, player.right_hand, player.light_on = direction, 'flashlight', 'pipe', True
    images = []
    font = pygame.font.SysFont('arial', 12)
    tree = next(street.props[i][1] for i, kind in street.scenery.effects.items() if kind == 'tree')
    for i in range(60):
        t = i / 15
        canvas = WorldCanvas((160, 85))
        canvas.fill((45, 48, 47))
        for player in actors:
            player.visual_time = t
            player.moving = 1.3 < t < 2.5
            player.walk_time = t if player.moving else 0
            player.swing = (t - 2.8) / .65 if 2.8 <= t <= 3.45 else None
            player.draw(canvas, 0, 0)
        canvas.blit(foliage_frame(tree, t * .95), (66, 4))
        for x, label in zip((18, 54, 90, 126), ('down', 'up', 'right', 'left')):
            canvas.surface.blit(font.render(label, True, (200, 200, 183)), (x * 2, 145))
        im = Image.frombytes('RGB', canvas.surface.get_size(), pygame.image.tobytes(canvas.surface, 'RGB'))
        images.append(im.resize((640, 340), Image.Resampling.NEAREST))
    output = ROOT / 'art_source/world-life.gif'
    images[0].save(output, save_all=True, append_images=images[1:], duration=67, loop=0, disposal=2)

    hero = Player((415, 523), frames)
    hero.facing, hero.left_hand, hero.right_hand, hero.light_on = 'up', 'flashlight', 'pipe', True
    camera = 260, 390
    panels = pygame.Surface((1920, 400))
    panels.fill((20, 22, 25))
    label_font = pygame.font.SysFont('arial', 18)
    for i, label in enumerate(('Ambient only', 'Flashlight: facade lit / roof blocks rays', 'Enemy nearby: VHS tracking damage')):
        canvas = WorldCanvas((GAME_W, GAME_H))
        canvas.fill((8, 8, 10))
        canvas.blit(street.map_surf, (-camera[0], -camera[1]))
        for _, image, x, y in street.scenery.props_at(0):
            canvas.blit(image, (x - camera[0], y - camera[1]))
        hero.draw(canvas, *camera)
        center = hero.rect.center
        if i == 0:
            canvas.blit(street.fog, (center[0] - camera[0] - GAME_W, center[1] - camera[1] - GAME_H))
        else:
            street.lighting.draw(canvas, street.fog, hero.flashlight_origin(), center, hero.facing, camera, street.light_blockers)
        if i == 2:
            tape = TapeDistortion(canvas.surface.get_size(), seed=17)
            tape.apply(canvas.surface, 1, .9)
        panels.blit(canvas.surface, (i * 640, 40))
        panels.blit(label_font.render(label, True, (210, 210, 190)), (i * 640 + 12, 10))
    pygame.image.save(panels, str(ROOT / 'art_source/lighting-vhs-preview.png'))
    pygame.quit()
    print(output)


if __name__ == '__main__':
    main()

"""Behavior checks for anchored animation, independent lamps and roof occlusion."""
import os
from pathlib import Path
import sys
import unittest
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from atmosphere import LampBank, TapeDistortion, foliage_frame
from characters import Player, build_hero_frames, build_monster_frames
from locations import LocationStore
from rendering import WorldCanvas
from settings import ART_SCALE, DIFFICULTIES, GAME_W, GAME_H
from lighting import merge_occluders


class WorldLifeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.hero = build_hero_frames()
        cls.store = LocationStore(build_monster_frames(), DIFFICULTIES['normal'])

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_hands_stay_on_sprite_in_every_walking_pose(self):
        player = Player((50, 50), self.hero)
        for direction in self.hero:
            player.facing = direction
            for index in range(5):
                player.moving = bool(index)
                player.walk_time = (index - 1) / 8 if index else 0
                frame = self.hero[direction]['walk'][index - 1] if index else self.hero[direction]['stand']
                for hand in ('left', 'right'):
                    x, y = (round(v * ART_SCALE) for v in player.hand_anchor(hand))
                    with self.subTest(direction=direction, pose=index, hand=hand):
                        self.assertTrue(any(frame.get_at((xx, yy)).a for yy in range(max(0, y - 1), min(38, y + 2))
                                            for xx in range(max(0, x - 1), min(24, x + 2))))

    def test_idle_and_tree_animation_preserve_feet_and_roots(self):
        for direction in self.hero.values():
            a, b = direction['idle']
            self.assertNotEqual(pygame.image.tobytes(a, 'RGBA'), pygame.image.tobytes(b, 'RGBA'))
            self.assertEqual(pygame.image.tobytes(a.subsurface((0, 28, 24, 10)), 'RGBA'),
                             pygame.image.tobytes(b.subsurface((0, 28, 24, 10)), 'RGBA'))
        street = self.store['street']
        index = next(i for i, kind in street.scenery.effects.items() if kind == 'tree')
        image = street.props[index][1]
        frame = foliage_frame(image, 1.4, 'tree')
        self.assertNotEqual(pygame.image.tobytes(image, 'RGBA'), pygame.image.tobytes(frame, 'RGBA'))
        root = pygame.Rect(0, image.get_height() - 10, image.get_width(), 10)
        self.assertEqual(pygame.image.tobytes(image.subsurface(root), 'RGBA'),
                         pygame.image.tobytes(frame.subsurface(root), 'RGBA'))

    def test_lamps_have_independent_finite_fault_bursts(self):
        bank = LampBank([('lamp', 20, 20), ('lamp', 100, 20)])
        history = [[], []]
        for _ in range(2400):
            bank.update(1 / 60)
            for i, lamp in enumerate(bank.lamps):
                history[i].append(lamp.level)
        self.assertNotEqual(history[0], history[1])
        for levels in history:
            self.assertIn(0, levels)
            first_fault = next(i for i, level in enumerate(levels) if level < .5)
            self.assertTrue(any(level == 1 for level in levels[first_fault + 180:]))

    def test_merged_light_blockers_preserve_door_gaps(self):
        original = [pygame.Rect(0, 0, 16, 16), pygame.Rect(16, 0, 16, 16),
                    pygame.Rect(0, 16, 16, 16), pygame.Rect(0, 48, 16, 16)]
        merged = merge_occluders(original)
        self.assertLess(len(merged), len(original))
        for y in range(64):
            for x in range(32):
                self.assertEqual(any(r.collidepoint(x, y) for r in original),
                                 any(r.collidepoint(x, y) for r in merged))

    def test_flashlight_lights_facade_but_not_roof_or_ground_behind_it(self):
        street = self.store['street']
        # Dark interior textures make the added light numerically measurable.
        shop = self.store['shop']
        roof = pygame.Rect(80, 60, 40, 30)
        origin = center = (100, 125)
        baseline, lit = WorldCanvas((GAME_W, GAME_H)), WorldCanvas((GAME_W, GAME_H))
        baseline.fill((70, 70, 70))
        lit.fill((70, 70, 70))
        baseline.blit(shop.fog, (center[0] - GAME_W, center[1] - GAME_H))
        shop.lighting.draw(lit, shop.fog, origin, center, 'up', (0, 0), [roof])
        for point in ((100, 78), (100, 45)):
            p = tuple(v * ART_SCALE for v in point)
            self.assertEqual(baseline.surface.get_at(p), lit.surface.get_at(p))
        p = 100 * ART_SCALE, 97 * ART_SCALE  # facade below the roof
        self.assertGreater(sum(lit.surface.get_at(p)[:3]), sum(baseline.surface.get_at(p)[:3]))
        self.assertGreaterEqual(len(street.light_blockers), 6)

    def test_vhs_is_inactive_when_safe_and_fades_after_threat(self):
        image = pygame.Surface((320, 180))
        image.fill((100, 110, 120))
        safe = pygame.image.tobytes(image, 'RGB')
        tape = TapeDistortion(image.get_size(), seed=4)
        tape.apply(image, 1 / 60, 0)
        self.assertEqual(safe, pygame.image.tobytes(image, 'RGB'))
        for _ in range(60):
            tape.apply(image, 1 / 60, 1)
        self.assertNotEqual(safe, pygame.image.tobytes(image, 'RGB'))
        for _ in range(240):
            image.fill((100, 110, 120))
            tape.apply(image, 1 / 60, 0)
        self.assertLess(tape.level, .008)
        self.assertEqual(safe, pygame.image.tobytes(image, 'RGB'))


if __name__ == '__main__':
    unittest.main()

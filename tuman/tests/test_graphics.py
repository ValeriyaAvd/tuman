"""Native resolution, transparency, frame grids and lossless presentation checks."""
import os
from pathlib import Path
import sys
import unittest
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from characters import build_hero_frames, build_monster_frames
from settings import DATA_DIR, ART_SCALE


class GraphicsTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def tearDown(self):
        pygame.quit()

    def test_every_active_image_has_double_native_resolution(self):
        root = Path(DATA_DIR)
        backup = root.parent / 'art_source/v1'
        for original in backup.rglob('*.png'):
            relative = original.relative_to(backup)
            if relative.name == 'hero_old.png':
                continue  # Unused archived sprite, deliberately retained as a reference.
            with self.subTest(asset=str(relative)):
                before = pygame.image.load(str(original))
                after = pygame.image.load(str(root / relative))
                self.assertEqual(after.get_size(), tuple(v * ART_SCALE for v in before.get_size()))
                nearest = pygame.transform.scale(before, after.get_size())
                self.assertNotEqual(pygame.image.tobytes(nearest, 'RGBA'), pygame.image.tobytes(after, 'RGBA'))

    def test_frame_grids_and_transparency(self):
        hero = build_hero_frames()
        for direction in ('down', 'up', 'left', 'right'):
            self.assertEqual(len(hero[direction]['walk']), 4)
            frames = [hero[direction]['stand']] + hero[direction]['walk']
            for frame in frames:
                self.assertEqual(frame.get_size(), (24, 38))
                self.assertEqual(frame.get_at((0, 0)).a, 0)
                self.assertGreater(pygame.mask.from_surface(frame).count(), 0)
        monster = build_monster_frames()
        self.assertEqual(monster[False]['stand'].get_size(), (24, 40))
        for path in (Path(DATA_DIR) / 'items').glob('*.png'):
            image = pygame.image.load(str(path))
            self.assertEqual(image.get_at((0, 0)).a, 0)

    def test_scene_presentation_preserves_native_pixels(self):
        from main import present
        scene = pygame.Surface((640, 360))
        scene.fill((19, 21, 23))
        for x in range(640):
            scene.fill(((x * 17) % 256, (x * 37) % 256, (x * 53) % 256), (x, 0, 1, 360))
        overlay = pygame.Surface((960, 540), pygame.SRCALPHA)
        display = pygame.display.set_mode((1280, 720))
        present(overlay, display, scene)
        expected = pygame.transform.scale(scene, (1280, 720))
        self.assertEqual(pygame.image.tobytes(display, 'RGB'), pygame.image.tobytes(expected, 'RGB'))


if __name__ == '__main__':
    unittest.main()

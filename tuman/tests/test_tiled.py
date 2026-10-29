"""Authored geometry preservation, lazy loading and Tiled integration checks."""
import base64
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from characters import build_monster_frames
from locations import LocationStore
from settings import DATA_DIR, DIFFICULTIES, ART_SCALE
from tiled_map import MapError, TiledMap, read_json


class TiledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.frames = build_monster_frames()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def store(self, root=None):
        return LocationStore(self.frames, DIFFICULTIES['hard'], root)

    def test_lazy_loading_doors_and_persistence(self):
        store = self.store()
        self.assertEqual(store.loaded, {})
        street = store['street']
        self.assertEqual(list(store.loaded), ['street'])
        street.monsters[0].dead = True
        shop, arrival = store.enter(street.doors[0])
        self.assertEqual(arrival, shop.start)
        returned, arrival = store.enter(shop.doors[0])
        self.assertIs(returned, street)
        self.assertTrue(returned.monsters[0].dead)
        self.assertEqual(arrival, street.spawns['from_shop'])
        self.assertEqual(shop.monsters[0].max_hp, DIFFICULTIES['hard']['monster_hp'])

    def test_new_map_discovery_and_base64(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = read_json(Path(DATA_DIR) / 'maps/shop.tmj')
            for ref in data['tilesets']:
                ref['source'] = str(Path(DATA_DIR) / 'maps' / ref['source'])
            layer = data['layers'][0]
            layer['data'] = base64.b64encode(zlib.compress(struct.pack(f'<{len(layer["data"])}I', *layer['data']))).decode()
            layer.update(encoding='base64', compression='zlib')
            # A genuinely new map with no Python registry edits.
            data['layers'] = [l for l in data['layers'] if l['name'] != 'Doors']
            (root / 'cellar.tmj').write_text(json.dumps(data), encoding='utf-8')
            (root / 'locations.json').write_text('{"start":"cellar"}', encoding='utf-8')
            store = self.store(root)
            self.assertEqual(list(store), ['cellar'])
            self.assertTrue(store['cellar'].inside)
            original = TiledMap(Path(DATA_DIR) / 'maps/shop.tmj')
            self.assertEqual(pygame.image.tobytes(original.surface, 'RGBA'),
                             pygame.image.tobytes(store['cellar'].map_surf, 'RGBA'))

    def test_unsupported_format_has_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.tmj'
            path.write_text('{"orientation":"isometric"}', encoding='utf-8')
            with self.assertRaisesRegex(MapError, 'bad.tmj.*Orthogonal'):
                TiledMap(path)

    def test_palette_collision_and_light_follow_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = read_json(Path(DATA_DIR) / 'maps/shop.tmj')
            for ref in data['tilesets']:
                ref['source'] = str(Path(DATA_DIR) / 'maps' / ref['source'])
            objects_ref = next(r for r in data['tilesets'] if r['source'].endswith('objects.tsj'))
            tileset = read_json(objects_ref['source'])
            lamp = next(t for t in tileset['tiles'] if t['image'] == 'lamp.png')
            data['layers'] = [{'type': 'objectgroup', 'objects': [
                {'gid': objects_ref['firstgid'] + lamp['id'], 'x': 40 * ART_SCALE, 'y': 80 * ART_SCALE,
                 'width': lamp['imagewidth'], 'height': lamp['imageheight']}]}]
            path = Path(tmp) / 'lamp.tmj'
            path.write_text(json.dumps(data), encoding='utf-8')
            tiled = TiledMap(path)
            self.assertEqual(len(tiled.decor), 1)
            self.assertEqual(len(tiled.walls), 5)
            self.assertEqual(tiled.walls[0], pygame.Rect(43, 76, 6, 4))
            self.assertEqual((tiled.objects[0]['x'], tiled.objects[0]['y']), (49, 51))

    def test_game_loop_visits_both_locations(self):
        import main as game
        from characters import Player
        players, stores = [], []
        frame = 0

        def player(*args, **kwargs):
            result = Player(*args, **kwargs)
            players.append(result)
            return result

        def locations(*args):
            result = LocationStore(*args)
            stores.append(result)
            return result

        def events():
            nonlocal frame
            frame += 1
            if frame == 1:
                self.assertEqual(list(stores[0].loaded), ['street'])
                return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)]  # car/flashlight
            if frame in (2, 4):
                keys = [pygame.K_i, pygame.K_f] if frame == 4 else [pygame.K_i]
                return [pygame.event.Event(pygame.KEYDOWN, key=key) for key in keys]
            if frame in (5, 8):
                target = stores[0]['street' if frame == 5 else 'shop'].doors[0].zone
                players[-1].rect.topleft = target.topleft
                players[-1].x, players[-1].y = target.topleft
            if frame in (6, 9):
                return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)]
            if frame == 11:
                self.assertEqual(set(stores[0].loaded), {'street', 'shop'})
                self.assertEqual(len(players), 3)
                return [pygame.event.Event(pygame.QUIT)]
            return []

        with patch.object(game, 'FULLSCREEN', False), patch.object(game, 'SKIP_MENU', True), \
             patch.object(game, 'SKIP_INTRO', True), patch.object(game, 'Player', player), \
             patch.object(game, 'build_locations', locations), patch.object(pygame.event, 'get', events):
            with self.assertRaises(SystemExit):
                game.main()
        pygame.init()
        pygame.display.set_mode((1, 1))


if __name__ == '__main__':
    unittest.main()

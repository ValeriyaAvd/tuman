"""Подсобка магазина: отмычка -> дверь -> код сейфа -> ключ -> ворота парка."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from characters import build_monster_frames
from locations import LocationStore
from settings import DIFFICULTIES
from texts import ITEMS


def spot(location, kind):
    return next(s for s in location.spots if s.kind == kind)


def door(location, target):
    return next(d for d in location.doors if d.target == target)


class OfficeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.frames = build_monster_frames()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_maps_are_wired(self):
        store = LocationStore(self.frames, DIFFICULTIES['normal'])
        street, shop, office = store['street'], store['shop'], store['office']
        self.assertEqual(spot(street, 'wreck').gives, 'lockpick')
        self.assertIsNone(spot(street, 'wreck').gives_if)          # отмычки лежат в машине с самого начала
        storeroom = door(shop, 'office')
        self.assertTrue(storeroom.locked)
        self.assertEqual(storeroom.requires, 'lockpick')
        safe = spot(office, 'safe')
        self.assertEqual((safe.code, safe.gives, safe.flag), ('1708', 'park_key', 'office_safe_open'))
        self.assertEqual(spot(street, 'gate').requires, 'park_key')
        for item in ('lockpick', 'park_key'):
            self.assertIn(item, ITEMS)
        # Закрытый и открытый сейф переключаются флагом
        names = lambda flags: {img.get_size() for _, img, _, _ in office.scenery.props_at(0, flags)}
        self.assertEqual(len(office.scenery.props_at(0)), len(office.scenery.props_at(0, {'office_safe_open'})))
        self.assertTrue(office.scenery.conditions)

    def test_quest_playthrough(self):
        import main as game
        from characters import Player
        players, stores = [], []
        frame = 0
        key = lambda k, u='': pygame.event.Event(pygame.KEYDOWN, key=k, unicode=u)
        E = key(pygame.K_e)

        def player(*args, **kwargs):
            result = Player(*args, **kwargs)
            players.append(result)
            return result

        def locations(*args):
            result = LocationStore(*args)
            stores.append(result)
            return result

        def put(rect):
            players[-1].rect.center = rect.center
            players[-1].x, players[-1].y = players[-1].rect.topleft

        script = []
        loc = lambda name: stores[0][name]
        wreck = lambda: spot(loc('street'), 'wreck')
        storeroom = lambda: door(loc('shop'), 'office')
        I, D = key(pygame.K_i), key(pygame.K_d)
        script += [lambda: put(wreck().zone), E, lambda: self.assertTrue(wreck().solved)]     # отмычки сразу в бардачке
        script += [lambda: put(spot(loc('street'), 'gate').zone), E]                   # ворота заперты
        script += [I, E, lambda: self.assertFalse(spot(loc('street'), 'gate').solved)]  # отмычки воротам не подходят
        script += [lambda: put(door(loc('street'), 'shop').zone), E]
        script += [lambda: put(storeroom().zone), E, E, lambda: self.assertTrue(storeroom().locked)]  # сама не открывается
        script += [I, E, lambda: self.assertFalse(storeroom().locked)]                 # применили отмычки из инвентаря
        script += [E]                                                                   # войти
        script += [lambda: self.assertFalse(storeroom().locked)]
        script += [lambda: put(spot(loc('office'), 'safe').zone), E,
                   [key(pygame.K_1, '1'), key(pygame.K_2, '2'), key(pygame.K_3, '3'), key(pygame.K_4, '4')],
                   lambda: self.assertFalse(spot(loc('office'), 'safe').solved),
                   E, [key(pygame.K_1, '1'), key(pygame.K_7, '7'), key(pygame.K_0, '0'), key(pygame.K_8, '8')],
                   lambda: self.assertTrue(spot(loc('office'), 'safe').solved)]
        script += [lambda: put(door(loc('office'), 'shop').zone), E]
        script += [lambda: put(door(loc('shop'), 'street').zone), E]
        script += [lambda: put(spot(loc('street'), 'gate').zone), E,
                   lambda: self.assertFalse(spot(loc('street'), 'gate').solved),
                   I, D, E, lambda: self.assertTrue(spot(loc('street'), 'gate').solved)]   # ключ из инвентаря

        def events():
            nonlocal frame
            frame += 1
            if frame == 1:
                return []
            if not script:
                return [pygame.event.Event(pygame.QUIT)]
            step = script.pop(0)
            if callable(step):
                step()
                return []
            return step if isinstance(step, list) else [step]

        with patch.object(game, 'FULLSCREEN', False), patch.object(game, 'SKIP_MENU', True), \
             patch.object(game, 'SKIP_INTRO', True), patch.object(game, 'Player', player), \
             patch.object(game, 'build_locations', locations), patch.object(pygame.event, 'get', events):
            with self.assertRaises(SystemExit):
                game.main()
        self.assertEqual(set(stores[0].loaded), {'street', 'shop', 'office'})
        self.assertFalse(spot(stores[0]['street'], 'gate').solved is False)
        pygame.init()
        pygame.display.set_mode((1, 1))


if __name__ == '__main__':
    unittest.main()

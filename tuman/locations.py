"""Discover Tiled maps and load each location on its first visit."""
import json
from collections.abc import Mapping
from pathlib import Path
import pygame
from settings import *
from world import make_fog, make_flashlight, make_light_grid, WALL_PASS
from characters import Monster
from story import Spot
from tiled_map import MapError, TiledMap, properties, read_json
from rendering import hd_effect
from atmosphere import LampBank, SceneryAnimator
from lighting import FlashlightRenderer, merge_occluders, facade_edges
from environment import WaterSystem


def json_lines(value, what):
    try:
        lines = json.loads(value)
    except (ValueError, TypeError):
        raise MapError(f'{what} must be a JSON array of strings.')
    if not isinstance(lines, list) or not lines or not all(isinstance(s, str) for s in lines):
        raise MapError(f'{what} must contain at least one string.')
    return lines


class Door:
    def __init__(self, obj):
        p = properties(obj)
        self.zone = pygame.Rect(obj['x'], obj['y'], obj['width'], obj['height'])
        self.target = p['target']
        self.spawn = p.get('spawn', 'entry')
        self.facing = p.get('facing', 'down')
        self.hint = p.get('hint', '[E] пройти')
        # Замок: requires — предмет из инвентаря, которым дверь открывается (например pipe)
        self.requires = p.get('requires') or None
        self.locked = self.requires is not None
        self.locked_lines = json_lines(p.get('locked', '["Заперто."]'), 'locked')
        self.locked_hint = p.get('locked_hint', '[E] осмотреть дверь')
        self.unlock_text = p.get('unlock', '')
        self.tries = 0
        self.try_flag = p.get('try_flag') or None   # флаг после первой попытки открыть запертую дверь
        if self.facing not in ('up', 'down', 'left', 'right'):
            raise MapError(f'Invalid door facing: {self.facing}')


class Location:
    def __init__(self, path, monster_frames, fogs, difficulty):
        tiled = TiledMap(path)
        self.name = Path(path).stem
        self.inside = tiled.props.get('inside', False)
        self.rows, self.walls = tiled.ground, tiled.walls
        self.map_surf, self.props = tiled.surface, tiled.decor
        self.puddles = list(tiled.puddles)
        self.light_blockers = list(tiled.light_blockers)
        light_regions = list(tiled.light_regions)
        light_facades = list(tiled.light_facades)
        self.fog, self.flashlight = fogs(self.inside)
        self.fog_full = FOG_INSIDE_FULL if self.inside else FOG_FULL
        self.glows, self.car_rects, self.pipe_rects = [], [], []
        self.spots, self.remarks, self.monsters, self.doors = [], [], [], []
        self.spawns = {}
        self.note_rect = None
        for obj in tiled.objects:
            kind = obj.get('class') or obj.get('type')
            p = properties(obj)
            rect = pygame.Rect(obj['x'], obj['y'], obj.get('width', 0), obj.get('height', 0))
            if any(obj.get(k) for k in ('ellipse', 'polygon', 'polyline')):
                tiled.fail(f'{obj.get("name")}: gameplay zones must be rectangles or points.')
            if kind == 'collision':
                self.walls.append(rect)
                light_rect = (pygame.Rect(*(v / ART_SCALE for v in json.loads(p['light_rect'])))
                              if 'light_rect' in p else rect)
                light_regions.append((light_rect, p.get('light_pass', WALL_PASS)))
            elif kind == 'light_blocker':
                self.light_blockers.append(rect)
                light_regions.append((rect, p.get('light_pass', 0)))
            elif kind == 'light_facade':
                self.light_blockers.extend(facade_edges(rect))
                light_facades.append((rect, rect.h + 2))
            elif kind == 'puddle':
                self.puddles.append(rect)
            elif kind == 'spawn':
                name = obj.get('name') or 'entry'
                if name in self.spawns:
                    tiled.fail(f'Duplicate spawn: {name}')
                self.spawns[name] = (obj['x'], obj['y'])
            elif kind == 'monster':
                monster = Monster((obj['x'], obj['y']), monster_frames)
                monster.max_hp = difficulty['monster_hp']
                monster.reset()
                self.monsters.append(monster)
            elif kind == 'door':
                self.doors.append(Door(obj))
            elif kind == 'car':
                self.car_rects.append(rect)
            elif kind == 'item':
                item = p.get('item')
                if item == 'pipe':
                    self.pipe_rects.append(rect)
                elif item == 'note':
                    if self.note_rect is not None:
                        tiled.fail('Only one note per map is supported.')
                    self.note_rect = rect
                else:
                    tiled.fail(f'Unknown item: {item}')
            elif kind == 'light':
                light = p.get('kind', 'lamp')
                if light not in ('lamp', 'lamp_broken', 'window', 'booth', 'fridge', 'flame', 'desk'):
                    tiled.fail(f'Unknown light kind: {light}')
                self.glows.append((light, obj['x'], obj['y']))
            elif kind == 'spot':
                try:
                    lines = json.loads(p.get('inspect', '[]'))
                except (ValueError, TypeError):
                    tiled.fail(f'{obj.get("name")}: inspect must be a JSON array of strings.')
                if not isinstance(lines, list) or not lines or not all(isinstance(s, str) for s in lines):
                    tiled.fail(f'{obj.get("name")}: inspect must contain at least one string.')
                spot = Spot(p.get('kind', 'scenery'), rect,
                            {'approach': p.get('approach') or None, 'inspect': lines})
                spot.code = p.get('code') or None          # кодовый замок (сейф)
                spot.requires = p.get('requires') or None  # нужен предмет (ключ от ворот)
                spot.gives = p.get('gives') or None        # что получаем, когда открыли
                spot.flag = p.get('flag') or None          # сюжетный флаг для show_if / hide_if
                spot.gives_if = p.get('gives_if') or None  # предмет появляется только после этого флага
                spot.found = p.get('found') or None        # реплика, когда предмет найден
                spot.opened_lines = (json_lines(p['opened'], f'{obj.get("name")}: opened')
                                     if 'opened' in p else None)
                if spot.requires and 'opened' not in p:
                    tiled.fail(f'{obj.get("name")}: requires needs opened lines.')
                spot.solved = False
                self.spots.append(spot)
            elif kind == 'remark':
                self.remarks.append([rect, p.get('text', ''), False])
            else:
                tiled.fail(f'Unknown object class: {kind}')
        if 'entry' not in self.spawns:
            tiled.fail('Add a point named entry with class spawn.')
        self.start = self.spawns['entry']
        if self.inside:
            self.light_blockers.extend(self.walls)
        self.light_grid = make_light_grid(self.rows, light_regions + light_facades)
        self.light_blockers = merge_occluders(self.light_blockers)
        self.lamps = LampBank(self.glows)
        self.scenery = SceneryAnimator(self.props, tiled.prop_effects, self.lamps, tiled.decor_conditions)
        self.ground_scenery = SceneryAnimator(tiled.ground_props, tiled.ground_effects, self.lamps)
        self.water = WaterSystem(self.puddles)
        self.lighting = FlashlightRenderer(self.inside, self.flashlight) if self.flashlight else None


class LocationStore(Mapping):
    def __init__(self, monster_frames, difficulty, maps_dir=None):
        self.root = Path(maps_dir or Path(DATA_DIR) / 'maps')
        self.paths = {p.stem: p for p in sorted(self.root.glob('*.tmj'))}
        if not self.paths:
            raise MapError(f'No .tmj maps in {self.root}')
        config = read_json(self.root / 'locations.json')
        self.start_name = config.get('start', 'street')
        if self.start_name not in self.paths:
            raise MapError(f'Unknown starting map: {self.start_name}')
        self.loaded = {}
        self.monster_frames, self.difficulty = monster_frames, difficulty
        self._fogs = {}

    def fogs(self, inside):
        if inside not in self._fogs:
            color, clear, full, alpha = ((FOG_INSIDE_COLOR, FOG_INSIDE_CLEAR, FOG_INSIDE_FULL, FOG_INSIDE_ALPHA)
                                         if inside else (FOG_COLOR, FOG_CLEAR, FOG_FULL, FOG_MAX_ALPHA))
            fog = make_fog(color, clear, full, alpha)
            self._fogs[inside] = hd_effect(fog), {direction: tuple(hd_effect(img) for img in images)
                for direction, images in make_flashlight(fog, color, alpha).items()}
        return self._fogs[inside]

    def __getitem__(self, name):
        if name not in self.paths:
            raise MapError(f'Unknown location {name!r}; available: {", ".join(self.paths)}')
        if name not in self.loaded:
            location = Location(self.paths[name], self.monster_frames, self.fogs, self.difficulty)
            for door in location.doors:
                if door.target not in self.paths:
                    raise MapError(f'{name}: door leads to missing map {door.target}')
            self.loaded[name] = location
        return self.loaded[name]

    def __iter__(self):
        return iter(self.paths)

    def __len__(self):
        return len(self.paths)

    def enter(self, door):
        location = self[door.target]
        if door.spawn not in location.spawns:
            raise MapError(f'{door.target}: missing destination spawn {door.spawn}')
        return location, location.spawns[door.spawn]


def build_locations(monster_frames, difficulty):
    return LocationStore(monster_frames, difficulty)

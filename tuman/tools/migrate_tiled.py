"""One-time import of the original prototype. Never needed to edit/play Tiled maps.

Run from the game directory: python tools/migrate_tiled.py
Refuses to overwrite authored maps unless --force is explicitly supplied.
"""
import argparse
import json
import math
import os
import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
from settings import DATA_DIR, TILE, ART_SCALE
from world import load_map, build_world, find_groups, GRASS_TILES
from story import build_spots, build_remarks
import world


def props(**values):
    return [{'name': k, 'type': 'bool' if isinstance(v, bool) else 'float' if isinstance(v, float)
             else 'int' if isinstance(v, int) else 'string', 'value': v} for k, v in values.items()]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def make_palette(root):
    """Small reusable palette, alongside the lossless imported map tiles."""
    terrain, scenery = [], []
    for name, symbol, ground in [('grass', ',', 'soft'), ('asphalt', '.', 'hard'),
                                  ('pavement', '_', 'hard'), ('floor', ':', 'hard'),
                                  ('puddle', '~', 'water'), ('road_line', '=', 'hard'),
                                  ('manhole', 'O', 'hard'), ('abyss', 'A', 'hard'), ('wall', 'W', 'hard')]:
        for variant in range(2):
            image = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            world.draw_ground(image, [symbol], random.Random(variant + 10))
            filename = f'{name}_{variant}.png'
            pygame.image.save(image, str(root / filename))
            tile = {'id': len(terrain), 'image': filename, 'imagewidth': TILE, 'imageheight': TILE,
                    'properties': props(name=name, ground=ground, solid=symbol in 'AW')}
            terrain.append(tile)

    def sprite(name, image, collisions, lights=(), sort_y=None):
        filename = f'{name}.png'
        pygame.image.save(image, str(root / filename))
        tile = {'id': len(scenery), 'image': filename, 'imagewidth': image.get_width(),
                'imageheight': image.get_height(), 'properties': props(name=name,
                sort_y=sort_y if sort_y is not None else image.get_height(),
                lights=json.dumps(lights)), 'objectgroup': {'type': 'objectgroup', 'objects': [
                    {'id': i + 1, 'x': r.x, 'y': r.y, 'width': r.w, 'height': r.h}
                    for i, r in enumerate(collisions)]}}
        scenery.append(tile)

    for name, fn, size in [('house', world.draw_house, (128, 96)), ('shop', world.draw_shop, (224, 96)),
                            ('shelf', world.draw_shelf, (64, 16)), ('fridge', world.draw_fridge, (48, 16))]:
        image = pygame.Surface((size[0] + 4, size[1] + 16), pygame.SRCALPHA)
        rect = pygame.Rect(0, 12, *size)
        lights = []
        if name == 'shelf':
            fn(image, rect, random.Random(7))
        else:
            fn(image, rect, random.Random(7), lights)
        sprite(name, image, [rect], lights, rect.bottom)
    for name, image, rect, lights in [
        ('tree', world.make_tree(random.Random(7)), pygame.Rect(11, 28, 6, 4), []),
        ('bush', world.make_bush(random.Random(7)), pygame.Rect(3, 11, 10, 4), []),
        ('lamp', world.make_lamp(False), pygame.Rect(3, 30, 6, 4), [('lamp', 9, 5)]),
        ('lamp_broken', world.make_lamp(True), pygame.Rect(3, 30, 6, 4), [('lamp_broken', 9, 5)]),
        ('fence', world.make_fence(), pygame.Rect(0, 11, 16, 4), [])]:
        sprite(name, image, [rect], lights)
    image = pygame.Surface((48, 32), pygame.SRCALPHA)
    world.draw_car(image, image.get_rect(), (112, 32, 34), False, random.Random(7))
    sprite('car', image, [image.get_rect()])
    for name, tiles in [('terrain', terrain), ('objects', scenery)]:
        save(root / f'{name}.tsj', {'type': 'tileset', 'version': '1.10', 'name': name.title(),
             'tilewidth': max(t['imagewidth'] for t in tiles),
             'tileheight': max(t['imageheight'] for t in tiles), 'objectalignment': 'bottomleft',
             'columns': 0, 'tilecount': len(tiles), 'tiles': tiles})
    return len(terrain), len(scenery)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if ART_SCALE != 1:
        parser.error('Legacy 16px converter is archived. Current art uses 32px tiles; edit maps directly in Tiled.')
    root = Path(DATA_DIR) / 'maps'
    if root.exists() and any(root.glob('*.tmj')) and not args.force:
        parser.error('Tiled maps already exist. Refusing to overwrite; use --force only to discard edits.')
    root.mkdir(exist_ok=True)
    tiles_dir = root / 'tilesets'
    tiles_dir.mkdir(exist_ok=True)
    pygame.init()
    pygame.display.set_mode((1, 1))
    atlas_tiles, atlas_lookup, decor_tiles, decor_lookup = [], {}, [], {}
    maps = []
    for name, file, inside in [('street', 'map.txt', False), ('shop', 'shop.txt', True)]:
        rows, walls, start, note, monsters = load_map(str(Path(__file__).resolve().parent / 'legacy' / file))
        surface, decor, lights = build_world(rows)
        width, height = len(rows[0]), len(rows)
        data = []
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                image = surface.subsurface((x * TILE, y * TILE, TILE, TILE)).copy()
                ground = 'water' if ch == '~' else 'soft' if ch in GRASS_TILES else 'hard'
                key = (pygame.image.tobytes(image, 'RGBA'), ground)
                if key not in atlas_lookup:
                    atlas_lookup[key] = len(atlas_tiles)
                    atlas_tiles.append((image, ground))
                data.append(atlas_lookup[key] + 1)
        objects = {k: [] for k in ('Decor', 'Collisions', 'Spawns', 'Doors', 'Items', 'Lights', 'Story')}
        next_id = 1

        def add(layer, object_class, rect=None, point=None, name='', **values):
            nonlocal next_id
            obj = {'id': next_id, 'name': name or object_class, 'type': object_class, 'rotation': 0, 'visible': True}
            if point is not None:
                obj.update(x=point[0], y=point[1], width=0, height=0, point=True)
            else:
                obj.update(x=rect.x, y=rect.y, width=rect.w, height=rect.h)
            obj['properties'] = props(**values)
            next_id += 1
            objects[layer].append(obj)
            return obj

        for bottom, image, x, y in decor:
            key = (pygame.image.tobytes(image, 'RGBA'), image.get_size(), bottom - y)
            if key not in decor_lookup:
                tile_id = len(decor_tiles)
                decor_lookup[key] = tile_id
                filename = f'decor_{tile_id:03}.png'
                pygame.image.save(image, str(tiles_dir / filename))
                decor_tiles.append({'id': tile_id, 'image': filename, 'imagewidth': image.get_width(),
                                    'imageheight': image.get_height(), 'properties': props(sort_y=bottom - y)})
            obj = add('Decor', '', pygame.Rect(x, y + image.get_height(), *image.get_size()), name='scenery')
            obj['gid'] = decor_lookup[key]  # firstgid assigned after the shared atlas is complete
        for wall in walls:
            add('Collisions', 'collision', wall)
        add('Spawns', 'spawn', point=start, name='entry')
        if name == 'street':
            add('Spawns', 'spawn', point=(25 * TILE + 4, 32 * TILE + 8), name='from_shop')
            add('Doors', 'door', pygame.Rect(25 * TILE, 32 * TILE, 2 * TILE, TILE), target='shop',
                spawn='entry', facing='up', hint='[E] войти в магазин')
        else:
            add('Doors', 'door', pygame.Rect(7 * TILE, 10 * TILE, TILE, TILE), target='street',
                spawn='from_shop', facing='down', hint='[E] выйти на улицу')
        for i, pos in enumerate(monsters):
            add('Spawns', 'monster', point=pos, name=f'monster_{i + 1}')
        for r in find_groups(rows, 'C'):
            add('Items', 'car', r)
        for r in find_groups(rows, 'I'):
            add('Items', 'item', r, item='pipe')
        if note:
            add('Items', 'item', note, item='note')
        for kind, x, y in lights:
            add('Lights', 'light', point=(x, y), name=kind, kind=kind)
        for i, spot in enumerate(build_spots(rows)):
            add('Story', 'spot', spot.zone, name=f'{spot.kind}_{i + 1}', kind=spot.kind,
                approach=spot.approach or '', inspect=json.dumps(spot.inspect, ensure_ascii=False))
        for r, text, _ in build_remarks(name):
            add('Story', 'remark', r, text=text)
        layers = [{'id': 1, 'name': 'Ground and buildings', 'type': 'tilelayer', 'width': width,
                   'height': height, 'x': 0, 'y': 0, 'opacity': 1, 'visible': True, 'data': data}]
        colors = {'Collisions': '#ff4444', 'Spawns': '#44dd88', 'Doors': '#55aaff',
                  'Items': '#ffdd55', 'Lights': '#ffff88', 'Story': '#cc88ff'}
        for i, (layer_name, items) in enumerate(objects.items(), 2):
            layers.append({'id': i, 'name': layer_name, 'type': 'objectgroup', 'draworder': 'topdown',
                           'opacity': 1, 'visible': True, 'color': colors.get(layer_name, '#ffffff'),
                           'objects': items})
        maps.append((name, {'type': 'map', 'version': '1.10', 'tiledversion': '1.11.2',
                           'orientation': 'orthogonal', 'renderorder': 'right-down', 'infinite': False,
                           'width': width, 'height': height, 'tilewidth': TILE, 'tileheight': TILE,
                           'nextlayerid': len(layers) + 1, 'nextobjectid': next_id,
                           'properties': props(inside=inside), 'layers': layers}))
    columns = 32
    atlas = pygame.Surface((columns * TILE, math.ceil(len(atlas_tiles) / columns) * TILE), pygame.SRCALPHA)
    for i, (image, _) in enumerate(atlas_tiles):
        atlas.blit(image, ((i % columns) * TILE, (i // columns) * TILE))
    pygame.image.save(atlas, str(tiles_dir / 'world.png'))
    save(tiles_dir / 'world.tsj', {'type': 'tileset', 'version': '1.10', 'name': 'World',
         'tilewidth': TILE, 'tileheight': TILE, 'columns': columns, 'tilecount': len(atlas_tiles),
         'image': 'world.png', 'imagewidth': atlas.get_width(), 'imageheight': atlas.get_height(),
         'tiles': [{'id': i, 'properties': props(ground=ground)} for i, (_, ground) in enumerate(atlas_tiles)]})
    save(tiles_dir / 'decor.tsj', {'type': 'tileset', 'version': '1.10', 'name': 'Decor',
         'tilewidth': max(t['imagewidth'] for t in decor_tiles),
         'tileheight': max(t['imageheight'] for t in decor_tiles), 'columns': 0,
         'objectalignment': 'bottomleft', 'tilecount': len(decor_tiles), 'tiles': decor_tiles})
    terrain_count, _ = make_palette(tiles_dir)
    for name, data in maps:
        data['tilesets'] = [{'firstgid': 1, 'source': 'tilesets/world.tsj'},
                            {'firstgid': len(atlas_tiles) + 1, 'source': 'tilesets/decor.tsj'},
                            {'firstgid': len(atlas_tiles) + len(decor_tiles) + 1, 'source': 'tilesets/terrain.tsj'},
                            {'firstgid': len(atlas_tiles) + len(decor_tiles) + terrain_count + 1, 'source': 'tilesets/objects.tsj'}]
        for obj in data['layers'][1]['objects']:
            obj['gid'] += len(atlas_tiles) + 1
        save(root / f'{name}.tmj', data)
    save(root / 'locations.json', {'start': 'street'})
    save(root / 'Tuman.tiled-project', {'folders': ['.'], 'extensionsPath': 'extensions',
                                      'automappingRulesFile': '', 'propertyTypes': []})
    pygame.quit()
    print(f'Converted 2 maps, {len(atlas_tiles)} world tiles, {len(decor_tiles)} decor sprites to {root}')


if __name__ == '__main__':
    main()

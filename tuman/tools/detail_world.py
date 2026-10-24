"""Author detailed native car sprites and Tiled scenery/roof metadata, once."""
import json
from pathlib import Path
import random
import shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / 'data/maps'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def props(obj):
    return {p['name']: p['value'] for p in obj.get('properties', [])}


def put(obj, name, value, kind='string'):
    properties = obj.setdefault('properties', [])
    properties[:] = [p for p in properties if p['name'] != name]
    properties.append({'name': name, 'type': kind, 'value': value})


def car(color, wreck=False, seed=1):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (96, 64))
    d = ImageDraw.Draw(im)
    shade = lambda k: tuple(round(v * k) for v in color)
    d.rounded_rectangle((4, 10, 94, 57), radius=9, fill=(18, 20, 23, 180))
    for x in (19, 70):
        for y in (7, 49):
            d.rounded_rectangle((x, y, x + 12, y + 8), radius=2, fill=(16, 17, 20))
            d.line((x + 3, y + 2, x + 10, y + 2), fill=(54, 54, 54))
    d.rounded_rectangle((2, 9, 92, 54), radius=8, fill=shade(.45), outline=(25, 24, 25), width=2)
    d.rounded_rectangle((5, 12, 89, 51), radius=7, fill=color, outline=shade(1.24))
    d.line((12, 13, 79, 13), fill=shade(1.42))
    d.line((12, 50, 78, 50), fill=shade(.62))
    # Cabin glass, rubber seals and the top-down roof panel.
    d.polygon([(24, 16), (58, 16), (70, 21), (70, 43), (58, 47), (24, 47), (18, 42), (18, 21)], fill=(17, 23, 28))
    d.polygon([(58, 18), (68, 22), (68, 42), (58, 45)], fill=(45, 65, 77) if not wreck else (62, 72, 76))
    d.line((60, 20, 65, 22, 65, 40), fill=(100, 123, 127), width=1)
    d.line((62, 20, 66, 23), fill=(151, 157, 146))
    d.polygon([(22, 20), (28, 18), (28, 45), (22, 43)], fill=(38, 53, 62))
    d.line((23, 23, 25, 21, 25, 35), fill=(81, 102, 111))
    d.rounded_rectangle((29, 17, 57, 46), radius=3, fill=shade(.88), outline=shade(.55))
    d.line((32, 19, 54, 19), fill=shade(1.23))
    for y in (15, 47):
        d.line((31, y, 56, y), fill=(24, 30, 32))
        d.line((35, y, 53, y), fill=(67, 81, 84))
    # Door seams, handles, mirrors, hood and boot creases.
    for y in (12, 49):
        d.line((31, y, 31, y + 3), fill=shade(.4))
        d.line((59, y, 59, y + 3), fill=shade(.4))
        d.line((37, y + 1, 42, y + 1), fill=(153, 148, 131))
    for y in (7, 53):
        d.rectangle((62, y, 66, y + 3), fill=(32, 33, 34))
        d.line((62, y, 65, y), fill=shade(1.2))
    d.line((72, 19, 85, 20, 86, 44, 72, 45), fill=shade(.66))
    d.line((74, 21, 84, 22), fill=shade(1.25))
    d.line((12, 21, 16, 21, 16, 43, 12, 43), fill=shade(.6))
    for y in (16, 43):
        d.rectangle((87, y, 91, y + 5), fill=(192, 177, 128) if not wreck else (103, 104, 93))
        d.line((88, y + 1, 88, y + 4), fill=(236, 222, 170) if not wreck else (142, 139, 118))
        d.rectangle((3, y + 1, 6, y + 4), fill=(153, 40, 33))
    d.line((91, 26, 91, 39), fill=(28, 31, 32), width=2)
    for y in range(27, 39, 3):
        d.point((92, y), fill=(139, 138, 121))
    d.rectangle((2, 29, 4, 36), fill=(150, 144, 117))
    d.line((3, 30, 3, 34), fill=(62, 62, 59))
    for _ in range(45 if wreck else 13):
        x, y = rnd.randrange(7, 86), rnd.choice((rnd.randrange(12, 16), rnd.randrange(48, 51)))
        d.line((x, y, x + rnd.randrange(1, 4), y), fill=rnd.choice([(68, 48, 35), (115, 82, 47), shade(.55)]))
    if wreck:
        d.line((64, 24, 62, 30, 66, 34, 61, 41), fill=(179, 187, 175))
        d.line((62, 30, 67, 28), fill=(145, 151, 143))
        d.line((44, 22, 46, 27, 42, 32), fill=shade(.48))
    return im


def main():
    backup = ROOT / 'art_source/life_before'
    backup.mkdir(parents=True, exist_ok=True)
    for path in [*MAPS.glob('*.tmj'), * (MAPS / 'tilesets').glob('*.tsj'), MAPS / 'tilesets/car.png']:
        target = backup / path.relative_to(MAPS)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(path, target)
    tiles = MAPS / 'tilesets'
    for name, color, wreck, seed in [('red', (108, 37, 33), False, 4),
                                     ('blue', (56, 69, 76), True, 8), ('tan', (89, 81, 58), True, 11)]:
        car(color, wreck, seed).save(tiles / f'car_{name}.png')
    car((108, 37, 33)).save(tiles / 'car.png')
    vehicles = {'type': 'tileset', 'version': '1.10', 'name': 'Vehicles', 'columns': 0,
                'tilewidth': 96, 'tileheight': 64, 'objectalignment': 'bottomleft', 'tilecount': 3,
                'tiles': [{'id': i, 'image': f'car_{name}.png', 'imagewidth': 96, 'imageheight': 64}
                          for i, name in enumerate(('red', 'blue', 'tan'))]}
    save(tiles / 'vehicles.tsj', vehicles)
    for file in ('objects.tsj', 'decor.tsj'):
        ts = read(tiles / file)
        for tile in ts['tiles']:
            image = tile.get('image')
            if image in ('tree.png', 'decor_000.png', 'decor_001.png'):
                put(tile, 'motion', 'tree')
            elif image in ('lamp.png', 'decor_005.png'):
                put(tile, 'motion', 'lamp')
            elif image in ('lamp_broken.png', 'decor_006.png'):
                put(tile, 'motion', 'lamp_broken')
            elif image in ('house.png', 'shop.png'):
                footprint = tile['objectgroup']['objects'][0]
                facade = 28 if image == 'house.png' else 36
                put(tile, 'roof_rect', json.dumps([footprint['x'], footprint['y'], footprint['width'], footprint['height'] - facade]))
        save(tiles / file, ts)
    for path in MAPS.glob('*.tmj'):
        data = read(path)
        if props(data).get('world_life_version'):
            continue
        all_objects = [obj for layer in data['layers'] for obj in layer.get('objects', [])]
        cells = {(round(o['x'] / 32), round(o['y'] / 32)) for o in all_objects
                 if (o.get('type') or o.get('class')) == 'collision' and o.get('width') == 32 and o.get('height') == 32}
        roofs = []
        for spot in all_objects:
            kind = props(spot).get('kind')
            if (spot.get('type') or spot.get('class')) != 'spot' or kind not in ('house', 'shop'):
                continue
            start = (int((spot['x'] + spot['width'] / 2) // 32), int((spot['y'] - 2) // 32))
            if start not in cells:
                raise ValueError(f'{path}: cannot locate building under {spot["name"]}')
            group, stack = {start}, [start]
            while stack:
                x, y = stack.pop()
                for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if p in cells and p not in group:
                        group.add(p)
                        stack.append(p)
            left, top = min(x for x, _ in group) * 32, min(y for _, y in group) * 32
            right, bottom = (max(x for x, _ in group) + 1) * 32, (max(y for _, y in group) + 1) * 32
            roofs.append({'id': data['nextobjectid'], 'name': f'roof_{spot["name"]}', 'type': 'light_blocker',
                          'x': left, 'y': top, 'width': right - left, 'height': bottom - top - (28 if kind == 'house' else 36),
                          'rotation': 0, 'visible': True})
            data['nextobjectid'] += 1
        if roofs:
            data['layers'].append({'id': data['nextlayerid'], 'name': 'Lighting occlusion', 'type': 'objectgroup',
                                   'color': '#bb5599', 'visible': False, 'opacity': 1, 'objects': roofs})
            data['nextlayerid'] += 1
        cars = [(o, 0) for o in all_objects if (o.get('type') or o.get('class')) == 'car']
        for i, spot in enumerate(o for o in all_objects if props(o).get('kind') == 'wreck'):
            cars.append(({'x': spot['x'] + 16, 'y': spot['y'] + 16,
                          'width': spot['width'] - 32, 'height': spot['height'] - 32}, i % 2 + 1))
        if cars:
            terrain = next(r for r in data['tilesets'] if r.get('source', '').endswith('terrain.tsj'))
            asphalt = terrain['firstgid'] + 2
            firstgid = max(r['firstgid'] + read(MAPS / r['source'])['tilecount'] for r in data['tilesets'])
            data['tilesets'].append({'firstgid': firstgid, 'source': 'tilesets/vehicles.tsj'})
            ground = next(l for l in data['layers'] if l['type'] == 'tilelayer')
            graphics = []
            for rect, variant in cars:
                for y in range(int(rect['y'] // 32), int((rect['y'] + rect['height']) // 32)):
                    for x in range(int(rect['x'] // 32), int((rect['x'] + rect['width']) // 32)):
                        ground['data'][y * ground['width'] + x] = asphalt
                graphics.append({'id': data['nextobjectid'], 'name': f'vehicle_{variant}', 'type': '',
                                 'gid': firstgid + variant, 'x': rect['x'], 'y': rect['y'] + rect['height'],
                                 'width': rect['width'], 'height': rect['height'], 'rotation': 0, 'visible': True})
                data['nextobjectid'] += 1
            data['layers'].append({'id': data['nextlayerid'], 'name': 'Vehicles', 'type': 'objectgroup',
                                   'visible': True, 'opacity': 1, 'draworder': 'topdown', 'objects': graphics})
            data['nextlayerid'] += 1
        put(data, 'world_life_version', 1, 'int')
        save(path, data)
    print('Detailed vehicles, independent canopy/lamp animation metadata and editable roof occluders installed.')


if __name__ == '__main__':
    main()

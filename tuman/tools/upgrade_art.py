"""One-time 2x art migration. Preserve original resources and authored Tiled geometry.

Environment art is generated from the prototype's procedural material definitions.
Character/item art is installed separately from the ImageGen production sheets.
Requires Pillow for authoring only; the game itself needs only pygame-ce.
"""
import json
import math
from pathlib import Path
import random
import shutil

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SOURCE = ROOT / 'art_source' / 'v1'


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def detailed_material(source):
    """Redraw code-generated materials at native 2x: bevels, grain and weathering."""
    src = source.convert('RGBA')
    dst = Image.new('RGBA', (src.width * 2, src.height * 2))
    old, new = src.load(), dst.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = old[x, y]
            if not a:
                continue
            north = old[x, max(0, y - 1)]
            west = old[max(0, x - 1), y]
            edge = min(8, max(-8, (r + g + b - sum(north[:3])) // 12))
            side = min(5, max(-5, (r + g + b - sum(west[:3])) // 18))
            organic = g > r + 3 and g > b + 2
            warm = r > b + 9
            for sy in range(2):
                for sx in range(2):
                    # Stable fine grain, directional relief and tiny pigment chips.
                    h = ((x * 374761393 + y * 668265263 + sx * 2246822519 + sy * 3266489917) & 0xffffffff)
                    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
                    grain = ((h >> 8) % 7) - 3
                    relief = (edge if sy == 0 else -edge // 2) + (side if sx == 0 else 0)
                    if organic:
                        delta = grain + (4 if sx == 0 and sy == 0 else -1)
                        tint = (delta - 1, delta + 1, delta - 2)
                    elif warm:
                        delta = grain + relief + (2 if sy == 0 else -2)
                        tint = (delta + 1, delta, delta - 1)
                    else:
                        delta = grain + relief
                        tint = (delta - 1, delta, delta + 1)
                    new[x * 2 + sx, y * 2 + sy] = tuple(max(0, min(255, c + d)) for c, d in zip((r, g, b), tint)) + (a,)
    return dst


def terrain(name, variant):
    rnd = random.Random(f'{name}:{variant}:32')
    colors = {'grass': (40, 50, 38), 'asphalt': (53, 55, 59), 'pavement': (82, 82, 84),
              'floor': (65, 62, 54), 'puddle': (53, 55, 59), 'road_line': (53, 55, 59),
              'manhole': (53, 55, 59), 'abyss': (9, 10, 13), 'wall': (70, 75, 68)}
    base = colors[name]
    image = Image.new('RGBA', (32, 32), base + (255,))
    draw = ImageDraw.Draw(image)
    for y in range(32):
        for x in range(32):
            n = rnd.choice((-4, -2, 0, 0, 0, 2, 3))
            image.putpixel((x, y), tuple(max(0, v + n) for v in base) + (255,))
    if name == 'grass':
        for _ in range(45):
            x, y = rnd.randrange(32), rnd.randrange(32)
            draw.line((x, y, x + rnd.choice((-1, 1)), y - rnd.randrange(1, 4)), fill=rnd.choice([(53, 65, 42), (29, 39, 29), (66, 68, 43)]))
        for _ in range(5):
            x, y = rnd.randrange(30), rnd.randrange(30)
            draw.line((x, y, x + 2, y + 1), fill=(86, 65, 39))
    elif name in ('asphalt', 'road_line', 'puddle', 'manhole'):
        for _ in range(35):
            x, y = rnd.randrange(32), rnd.randrange(32)
            draw.point((x, y), fill=rnd.choice([(79, 79, 78), (38, 40, 43), (64, 65, 63)]))
        crack = [(3, 0), (6, 6), (5, 12), (10, 16), (9, 21), (12, 27), (11, 31)]
        draw.line(crack, fill=(31, 33, 36))
        if name == 'road_line':
            for x in range(32):
                for y in range(14, 18):
                    if rnd.random() > 0.18:
                        draw.point((x, y), fill=rnd.choice([(155, 150, 124), (131, 129, 109), (170, 162, 132)]))
        elif name == 'puddle':
            draw.polygon([(4, 14), (11, 9), (23, 8), (29, 15), (26, 23), (13, 25), (3, 20)], fill=(30, 39, 47))
            draw.line((9, 15, 17, 13, 24, 14), fill=(70, 86, 96))
            draw.line((7, 21, 12, 22, 20, 21), fill=(49, 62, 72))
        elif name == 'manhole':
            draw.ellipse((2, 2, 29, 29), fill=(30, 32, 35), outline=(88, 82, 68))
            draw.ellipse((4, 4, 27, 27), fill=(49, 50, 51), outline=(20, 24, 27))
            for y in range(9, 25, 4):
                draw.line((8, y, 23, y), fill=(28, 31, 33))
                draw.line((8, y + 1, 23, y + 1), fill=(68, 67, 63))
            for x, y in [(7, 15), (24, 15), (15, 6), (15, 25)]:
                draw.point((x, y), fill=(112, 94, 65))
    elif name in ('pavement', 'floor'):
        step = 16 if name == 'pavement' else 32
        for y in range(0, 32, step):
            draw.line((0, y, 31, y), fill=(44, 46, 45))
            draw.line((0, y + 1, 31, y + 1), fill=(104, 101, 91))
        for x in ((0, 16) if variant == 0 else (8, 24)):
            draw.line((x, 0, x, 31), fill=(46, 47, 43))
            draw.line((x + 1, 0, x + 1, 31), fill=(98, 96, 85))
        draw.line([(27, 8), (25, 12), (27, 17), (24, 23)], fill=(41, 43, 41))
        for _ in range(8):
            x, y = rnd.randrange(31), rnd.randrange(31)
            draw.line((x, y, x + 1, y), fill=(42, 43, 39))
    elif name == 'wall':
        for x in range(3, 32, 7):
            draw.line((x, 0, x, 31), fill=(53, 62, 56))
            draw.line((x + 1, 0, x + 1, 31), fill=(88, 89, 75))
        draw.rectangle((0, 26, 31, 31), fill=(46, 37, 32))
        draw.line((0, 26, 31, 26), fill=(93, 76, 57))
        draw.line((23, 4, 24, 10, 21, 15, 23, 21), fill=(36, 43, 38))
    return image


def scale_metadata(value):
    """Spatial fields are pixels; IDs, tile counts and cell coordinates stay untouched."""
    for key in ('x', 'y', 'width', 'height', 'tilewidth', 'tileheight', 'imagewidth', 'imageheight',
                'offsetx', 'offsety', 'margin', 'spacing'):
        if key in value:
            value[key] *= 2
    for prop in value.get('properties', []):
        if prop['name'] == 'sort_y':
            prop['value'] *= 2
        elif prop['name'] == 'lights':
            prop['value'] = json.dumps([[kind, x * 2, y * 2] for kind, x, y in json.loads(prop['value'])])
    for key in ('tiles', 'objects'):
        for child in value.get(key, []):
            scale_metadata(child)
    if 'objectgroup' in value:
        scale_metadata(value['objectgroup'])
    if 'tileoffset' in value:
        scale_metadata(value['tileoffset'])


def scale_map(data):
    data['tilewidth'] *= 2
    data['tileheight'] *= 2

    def layers(items):
        for layer in items:
            for key in ('offsetx', 'offsety'):
                if key in layer:
                    layer[key] *= 2
            if layer['type'] == 'objectgroup':
                for obj in layer.get('objects', []):
                    scale_metadata(obj)
            elif layer['type'] == 'group':
                layers(layer['layers'])
    layers(data['layers'])


def main():
    if (DATA / 'art_manifest.json').exists():
        raise SystemExit('Already migrated. Refusing to overwrite authored graphics or rescale maps again.')
    SOURCE.mkdir(parents=True, exist_ok=True)
    # Snapshot all original resources, including any edits made in Tiled since migration.
    for path in DATA.rglob('*'):
        if path.is_file() and path.suffix in ('.png', '.tmj', '.tsj', '.json'):
            target = SOURCE / path.relative_to(DATA)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise SystemExit(f'Backup already exists: {target}; inspect it before retrying.')
            shutil.copy2(path, target)
    tiles = DATA / 'maps' / 'tilesets'
    for path in sorted(tiles.glob('*.png')):
        source = Image.open(SOURCE / path.relative_to(DATA))
        stem = path.stem
        terrain_name = stem.rsplit('_', 1)[0]
        if terrain_name in {'grass', 'asphalt', 'pavement', 'floor', 'puddle', 'road_line', 'manhole', 'abyss', 'wall'}:
            result = terrain(terrain_name, int(stem.rsplit('_', 1)[1]))
        else:
            result = detailed_material(source)
        result.save(path)
    for path in tiles.glob('*.tsj'):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        # Atlas/collection width and height refer to pixels, not grid counts.
        scale_metadata(data)
        save_json(path, data)
    for path in (DATA / 'maps').glob('*.tmj'):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        scale_map(data)
        save_json(path, data)
    # Effects are regenerated at native resolution from a smooth periodic field.
    fog = Image.new('RGBA', (384, 384))
    for y in range(384):
        for x in range(384):
            u, v = x * 2 * math.pi / 384, y * 2 * math.pi / 384
            cloud = (math.sin(u + math.cos(v * 2)) + math.sin(v * 3 - u * 2) * .45
                     + math.sin(u * 5 + v * 4) * .18 + math.cos(u * 11 - v * 7) * .06)
            alpha = round(max(0, min(78, (cloud + .2) * 35)))
            fog.putpixel((x, y), (166, 170, 174, alpha))
    fog.save(DATA / 'fog_clouds.png')
    exclaim = Image.new('RGBA', (14, 20))
    draw = ImageDraw.Draw(exclaim)
    draw.rectangle((4, 1, 10, 13), fill=(30, 25, 26, 255))
    draw.rectangle((4, 15, 10, 19), fill=(30, 25, 26, 255))
    draw.rectangle((5, 1, 8, 11), fill=(231, 219, 185, 255))
    draw.rectangle((6, 2, 8, 9), fill=(255, 247, 218, 255))
    draw.rectangle((5, 15, 8, 17), fill=(247, 235, 201, 255))
    exclaim.save(DATA / 'exclaim.png')
    save_json(DATA / 'art_manifest.json', {'version': 2, 'scale': 2, 'tile_pixels': 32,
        'hero_frame': [24, 38], 'monster_frame': [24, 40], 'source': 'art_source/v1',
        'environment': 'Native procedural material detail and terrain redraw',
        'characters_items': 'ImageGen sheets, fitted to production frame grids'})
    print('Environment, effects and all Tiled geometry upgraded to 2x; original resources preserved in art_source/v1.')


if __name__ == '__main__':
    main()

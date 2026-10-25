"""Finite orthogonal Tiled JSON maps. No dependency on Tiled at runtime."""
import base64
import gzip
import json
import struct
import zlib
from pathlib import Path

import pygame

from settings import TILE, ART_SCALE


class MapError(ValueError):
    pass


def properties(obj):
    return {p['name']: p['value'] for p in obj.get('properties', [])}


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise MapError(f'{path}: {exc}') from exc


class TiledMap:
    def __init__(self, path):
        self.path = Path(path)
        self.data = read_json(path)
        d = self.data
        if d.get('orientation') != 'orthogonal' or d.get('infinite', False):
            self.fail('Use a finite Orthogonal map.')
        if d.get('renderorder', 'right-down') != 'right-down':
            self.fail('Use Right Down render order.')
        self.tile_size = TILE * ART_SCALE
        if (d.get('tilewidth'), d.get('tileheight')) != (self.tile_size, self.tile_size):
            self.fail(f'Tile size must be {self.tile_size}x{self.tile_size}.')
        self.width, self.height = d['width'], d['height']
        if self.width <= 0 or self.height <= 0:
            self.fail('Map dimensions must be positive.')
        self.props = properties(d)
        self.tiles = {}
        self.images = {}
        self.surface = pygame.Surface((self.width * self.tile_size, self.height * self.tile_size))
        self.surface.fill(pygame.Color(d.get('backgroundcolor', '#08080a')))
        self.walls, self.decor, self.objects = [], [], []
        self.prop_effects, self.light_blockers = {}, []
        self.light_regions, self.light_facades = [], []
        self.ground_props, self.ground_effects = [], {}
        self.puddles = []
        self.ground = [['.' for _ in range(self.width)] for _ in range(self.height)]
        for ref in d.get('tilesets', []):
            self.load_tileset(ref)
        self.layers(d.get('layers', []))
        # Maps are closed worlds. Prevent walking off an unpainted map edge.
        w, h = self.width * TILE, self.height * TILE
        self.walls.extend([pygame.Rect(-TILE, -TILE, w + TILE * 2, TILE),
                           pygame.Rect(-TILE, h, w + TILE * 2, TILE),
                           pygame.Rect(-TILE, 0, TILE, h), pygame.Rect(w, 0, TILE, h)])

    def fail(self, message):
        raise MapError(f'{self.path}: {message}')

    def image(self, path):
        path = Path(path).resolve()
        if path not in self.images:
            try:
                self.images[path] = pygame.image.load(str(path)).convert_alpha()
            except (OSError, pygame.error) as exc:
                self.fail(f'Cannot load image {path}: {exc}')
        return self.images[path]

    def load_tileset(self, ref):
        first = ref['firstgid']
        if 'source' in ref:
            source = self.path.parent / ref['source']
            if source.suffix.lower() != '.tsj':
                self.fail('External tilesets must be saved as JSON (.tsj).')
            ts, root = read_json(source), source.parent
        else:
            ts, root = ref, self.path.parent
        definitions = {t['id']: t for t in ts.get('tiles', [])}
        if any(t.get('animation') for t in definitions.values()):
            self.fail('Animated tiles are unsupported; use static tiles.')
        offset = ts.get('tileoffset', {})
        if ts.get('objectalignment', 'bottomleft') not in ('unspecified', 'bottomleft'):
            self.fail('Tileset object alignment must be Bottom Left.')
        if ts.get('image'):
            sheet = self.image(root / ts['image'])
            tw, th = ts['tilewidth'], ts['tileheight']
            spacing, margin = ts.get('spacing', 0), ts.get('margin', 0)
            columns = ts['columns']
            for i in range(ts['tilecount']):
                rect = pygame.Rect(margin + (i % columns) * (tw + spacing),
                                   margin + (i // columns) * (th + spacing), tw, th)
                self.tiles[first + i] = (sheet.subsurface(rect), definitions.get(i, {}), offset)
        else:
            for i, tile in definitions.items():
                self.tiles[first + i] = (self.image(root / tile['image']), tile, offset)

    def tile(self, gid):
        raw = gid & 0x0fffffff
        if raw not in self.tiles:
            self.fail(f'Unknown tile GID {raw}.')
        image, definition, offset = self.tiles[raw]
        h, v, diagonal = bool(gid & 0x80000000), bool(gid & 0x40000000), bool(gid & 0x20000000)
        if diagonal:
            image = pygame.transform.flip(pygame.transform.rotate(image, 90), True, False)
        if h or v:
            image = pygame.transform.flip(image, h, v)
        return image, definition, offset

    def decode(self, layer):
        data = layer.get('data', [])
        if isinstance(data, str):
            if layer.get('encoding') != 'base64':
                self.fail('Use CSV or Base64 tile layer format.')
            data = base64.b64decode(data)
            compression = layer.get('compression', '')
            if compression == 'zlib':
                data = zlib.decompress(data)
            elif compression == 'gzip':
                data = gzip.decompress(data)
            elif compression:
                self.fail(f'Unsupported compression: {compression}; use zlib, gzip or none.')
            data = list(struct.unpack(f'<{len(data) // 4}I', data))
        if len(data) != layer['width'] * layer['height']:
            self.fail(f'Invalid tile count in layer {layer["name"]}.')
        return data

    def layers(self, layers, ox=0, oy=0, visible=True, opacity=1):
        for layer in layers:
            x = ox + layer.get('offsetx', 0)
            y = oy + layer.get('offsety', 0)
            shown = visible and layer.get('visible', True)
            alpha = opacity * layer.get('opacity', 1)
            kind = layer['type']
            if kind == 'group':
                self.layers(layer['layers'], x, y, shown, alpha)
            elif kind == 'tilelayer' and shown:
                for i, gid in enumerate(self.decode(layer)):
                    if not gid:
                        continue
                    tx, ty = i % layer['width'] + layer.get('x', 0), i // layer['width'] + layer.get('y', 0)
                    image, definition, offset = self.tile(gid)
                    px = x + tx * self.tile_size + offset.get('x', 0)
                    py = y + (ty + 1) * self.tile_size - image.get_height() + offset.get('y', 0)
                    self.draw_tile(image, definition, px, py, alpha, properties(layer).get('depth_sort', False), gid)
                    ground = properties(definition).get('ground')
                    if ground and 0 <= tx < self.width and 0 <= ty < self.height:
                        self.ground[ty][tx] = {'soft': ',', 'water': '~', 'hard': '.'}.get(ground, '.')
                        if ground == 'water':
                            self.puddles.append(pygame.Rect((x + tx * self.tile_size) / ART_SCALE,
                                                           (y + ty * self.tile_size) / ART_SCALE, TILE, TILE))
            elif kind == 'objectgroup':
                # Visibility controls editor helpers/graphics, never game logic.
                for obj in layer.get('objects', []):
                    if 'template' in obj:
                        self.fail('Object templates are unsupported; use Detach Template before saving.')
                    obj = dict(obj, x=obj.get('x', 0) + x, y=obj.get('y', 0) + y)
                    if obj.get('rotation', 0):
                        self.fail(f'Object {obj.get("name")}: rotation is unsupported; use tile flips.')
                    if 'gid' in obj and shown and obj.get('visible', True):
                        image, definition, offset = self.tile(obj['gid'])
                        w, h = obj.get('width', image.get_width()), obj.get('height', image.get_height())
                        if (w, h) != image.get_size():
                            self.fail('Resize tile images in the tileset, not tile objects.')
                        self.draw_tile(image, definition, obj['x'] + offset.get('x', 0),
                                       obj['y'] - h + offset.get('y', 0), alpha,
                                       not properties(layer).get('ground', False), obj['gid'])
                    if obj.get('class') or obj.get('type'):
                        obj = dict(obj, **{key: obj.get(key, 0) / ART_SCALE for key in ('x', 'y', 'width', 'height')})
                        self.objects.append(obj)
            elif kind not in ('tilelayer', 'objectgroup', 'group'):
                self.fail(f'Unsupported layer type: {kind}. Use tile, object or group layers.')

    def draw_tile(self, image, definition, x, y, alpha, depth, gid):
        p = properties(definition)
        ground_motion = p.get('ground_detail', False) and p.get('motion')
        depth = not p.get('ground_detail', False) and (depth or bool(p.get('motion')))
        if alpha != 1:
            image = image.copy()
            image.set_alpha(round(alpha * 255))
        if ground_motion:
            self.ground_effects[len(self.ground_props)] = p['motion']
            self.ground_props.append(((y + image.get_height()) / ART_SCALE, image, x / ART_SCALE, y / ART_SCALE))
        elif depth:
            if p.get('motion'):
                self.prop_effects[len(self.decor)] = p['motion']
            self.decor.append(((y + p.get('sort_y', image.get_height())) / ART_SCALE, image, x / ART_SCALE, y / ART_SCALE))
        else:
            self.surface.blit(image, (x, y))
        if p.get('roof_rect'):
            roof = pygame.Rect(json.loads(p['roof_rect']))
            iw, ih = image.get_size()
            if gid & 0x20000000:
                roof = pygame.Rect(iw - roof.bottom, ih - roof.right, roof.h, roof.w)
            if gid & 0x80000000:
                roof.x = iw - roof.right
            if gid & 0x40000000:
                roof.y = ih - roof.bottom
            roof.move_ip(x, y)
            self.light_blockers.append(pygame.Rect(*(round(v / ART_SCALE) for v in roof)))
            self.light_regions.append((pygame.Rect(*(round(v / ART_SCALE) for v in roof)), 0))
        if p.get('facade_rect'):
            # Two side strips leave the visible front face open to light from below.
            from lighting import facade_edges
            facade = pygame.Rect(json.loads(p['facade_rect']))
            iw, ih = image.get_size()
            if gid & 0x20000000:
                facade = pygame.Rect(iw - facade.bottom, ih - facade.right, facade.h, facade.w)
            if gid & 0x80000000:
                facade.x = iw - facade.right
            if gid & 0x40000000:
                facade.y = ih - facade.bottom
            facade.move_ip(x, y)
            self.light_blockers.extend(facade_edges(pygame.Rect(*(round(v / ART_SCALE) for v in facade))))
            logical_facade = pygame.Rect(*(round(v / ART_SCALE) for v in facade))
            self.light_facades.append((logical_facade, logical_facade.h + 2))
        for kind, lx, ly in json.loads(p.get('lights', '[]')):
            iw, ih = image.get_size()
            if gid & 0x20000000:
                lx, ly = iw - ly, ih - lx
            if gid & 0x80000000:
                lx = iw - lx
            if gid & 0x40000000:
                ly = ih - ly
            self.objects.append({'type': 'light', 'x': (x + lx) / ART_SCALE, 'y': (y + ly) / ART_SCALE,
                                 'properties': [{'name': 'kind', 'value': kind}]})
        collisions = definition.get('objectgroup', {}).get('objects', [])
        if p.get('solid'):
            original = self.tiles[gid & 0x0fffffff][0]
            collisions = [{'x': 0, 'y': 0, 'width': original.get_width(), 'height': original.get_height()}]
        for c in collisions:
            if any(c.get(k) for k in ('ellipse', 'polygon', 'polyline', 'rotation')):
                self.fail('Tile collisions must be unrotated rectangles.')
            r = pygame.Rect(c['x'], c['y'], c['width'], c['height'])
            iw, ih = image.get_size()
            if gid & 0x20000000:
                r = pygame.Rect(iw - r.bottom, ih - r.right, r.h, r.w)
            if gid & 0x80000000:
                r.x = iw - r.right
            if gid & 0x40000000:
                r.y = ih - r.bottom
            r = r.move(x, y)
            logical_rect = pygame.Rect(*(round(v / ART_SCALE) for v in r))
            self.walls.append(logical_rect)
            self.light_regions.append((logical_rect, p.get("light_pass", 2)))

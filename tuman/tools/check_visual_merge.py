"""Verify this graphics transplant against the unmodified gameplay baseline.

Run from tuman/: python tools/check_visual_merge.py
The fixture records the original project before its visual layers were replaced.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from tiled_map import TiledMap


def gameplay(tiled):
    return {
        'size': [tiled.width, tiled.height], 'properties': tiled.props,
        'objects': tiled.objects, 'walls': [list(r) for r in tiled.walls],
        'ground': tiled.ground, 'puddles': [list(r) for r in tiled.puddles],
        'light_blockers': [list(r) for r in tiled.light_blockers],
        'light_regions': [[list(r), v] for r, v in tiled.light_regions],
        'light_facades': [[list(r), v] for r, v in tiled.light_facades],
    }


def main():
    baseline = json.loads((ROOT / 'tests/fixtures/visual_merge.json').read_text(encoding='utf-8'))
    pygame.init()
    pygame.display.set_mode((1, 1))
    try:
        for name, expected in baseline['gameplay_sha256'].items():
            tiled = TiledMap(ROOT / f'data/maps/{name}.tmj')
            data = json.dumps(gameplay(tiled), sort_keys=True, ensure_ascii=False).encode('utf-8')
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f'{name}: gameplay differs from the original version')
            print(f'{name}: original geometry, quests, items, ground, water and light preserved')
        for key in ('runtime_python_sha256', 'protected_art_sha256'):
            for name, expected in baseline[key].items():
                if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
                    raise ValueError(f'Original file changed: {name}')
        print(f"All {len(baseline['runtime_python_sha256'])} runtime Python modules unchanged.")
        print('Original firs, hopscotch, notice board, lake poster and office art preserved.')
    except (ValueError, OSError) as exc:
        print(f'VISUAL MERGE ERROR: {exc}', file=sys.stderr)
        return 1
    finally:
        pygame.quit()
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Pack approved ImageGen sheets into the game's exact native frame grids.

Cropping, palette reduction and nearest-neighbour fitting are build preparation;
the drawings themselves come from ImageGen. No runtime Pillow dependency.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def fit_cell(cell, size, padding=1, colors=64):
    cell = cell.convert('RGBA')
    alpha = cell.getchannel('A').point(lambda value: 255 if value >= 160 else 0)
    cell.putalpha(alpha)
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError('Empty generated sprite cell')
    cell = cell.crop(bounds)
    scale = min((size[0] - padding * 2) / cell.width, (size[1] - padding * 2) / cell.height)
    cell = cell.resize((max(1, round(cell.width * scale)), max(1, round(cell.height * scale))), Image.Resampling.NEAREST)
    # A bounded palette avoids gradients after fitting to a tiny native sprite.
    alpha = cell.getchannel('A')
    cell = cell.convert('RGB').quantize(colors=colors, dither=Image.Dither.NONE).convert('RGBA')
    cell.putalpha(alpha)
    output = Image.new('RGBA', size)
    output.paste(cell, ((size[0] - cell.width) // 2, size[1] - padding - cell.height))
    return output


def sheet(name, columns, rows, frame_size, source_path=None):
    source = Image.open(source_path or ROOT / 'art_source/generated' / f'{name}.png')
    target = Image.new('RGBA', (frame_size[0] * columns, frame_size[1] * rows))
    for y in range(rows):
        for x in range(columns):
            cell = source.crop((round(source.width * x / columns), round(source.height * y / rows),
                                round(source.width * (x + 1) / columns), round(source.height * (y + 1) / rows)))
            target.paste(fit_cell(cell, frame_size), (frame_size[0] * x, frame_size[1] * y))
    destination = ROOT / 'data' / f'{name}.png'
    temporary = destination.with_suffix('.new.png')
    target.save(temporary)
    temporary.replace(destination)
    return target


def main():
    hero_source = ROOT / 'art_source/generated/hero-ref-v3.png'
    hero = sheet('hero', 5, 3, (24, 38), hero_source if hero_source.exists() else None)
    monster = sheet('monster', 2, 1, (24, 40))
    source = Image.open(ROOT / 'art_source/generated/items.png')
    targets = [('flashlight_icon', (32, 32)), ('note_icon', (32, 32)), ('pipe_icon', (32, 32)),
               ('pipe_ground', (34, 28)), ('flashlight_hand_off', (14, 10)), ('flashlight_hand_on', (14, 10))]
    for i, (name, size) in enumerate(targets):
        x, y = i % 3, i // 3
        cell = source.crop((round(source.width * x / 3), round(source.height * y / 2),
                            round(source.width * (x + 1) / 3), round(source.height * (y + 1) / 2)))
        fit_cell(cell, size, padding=0 if 'hand' in name else 1, colors=48).save(ROOT / 'data/items' / f'{name}.png')
    preview = Image.new('RGB', (960, 440), (23, 25, 28))
    hero_preview = hero.resize((480, 456), Image.Resampling.NEAREST).crop((0, 0, 480, 152))
    monster_preview = monster.resize((192, 160), Image.Resampling.NEAREST)
    preview.paste(hero_preview, (24, 24), hero_preview)
    preview.paste(monster_preview, (600, 24), monster_preview)
    for i, (name, size) in enumerate(targets[:4]):
        img = Image.open(ROOT / 'data/items' / f'{name}.png')
        preview.paste(img.resize((size[0] * 4, size[1] * 4), Image.Resampling.NEAREST), (24 + i * 180, 240),
                      img.getchannel('A').resize((size[0] * 4, size[1] * 4), Image.Resampling.NEAREST))
    preview.save(ROOT / 'art_source/sprites-preview.png')
    print('Installed hero 120x114, monster 48x40 and six item sprites. Native pixels, bounded palettes, binary alpha.')


if __name__ == '__main__':
    main()

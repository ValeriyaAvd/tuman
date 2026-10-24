"""Native pixel-art authoring and one-time Tiled dressing pass. Existing edits are snapshotted."""
import json
import math
from pathlib import Path
import random
import shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / 'data/maps'
TILES = MAPS / 'tilesets'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, data):
    temporary = path.with_suffix(path.suffix + '.new')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def png(path, image):
    temporary = path.with_suffix('.new.png')
    image.save(temporary)
    temporary.replace(path)


def props(obj):
    return {p['name']: p['value'] for p in obj.get('properties', [])}


def put(obj, key, value):
    obj.setdefault('properties', [])[:] = [p for p in obj.get('properties', []) if p['name'] != key]
    obj['properties'].append({'name': key, 'type': 'bool' if isinstance(value, bool) else 'int' if isinstance(value, int) else 'string', 'value': value})


def tree(seed=1, bare=False):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (56, 64))
    d = ImageDraw.Draw(im)
    d.polygon([(26, 26), (30, 26), (32, 57), (38, 63), (29, 61), (21, 63), (25, 56)], fill=(47, 39, 29))
    d.line((28, 31, 29, 57, 31, 61), fill=(87, 71, 47), width=2)
    d.line((25, 44, 25, 57, 22, 61), fill=(25, 28, 22))
    for end in ((9, 20), (14, 8), (27, 3), (43, 10), (49, 27), (13, 37)):
        d.line((28, 45, 27, 30, end[0], end[1]), fill=(55, 48, 35), width=2)
        d.line((end[0], end[1], end[0] + rnd.choice((-4, 4)), max(2, end[1] - 6)), fill=(75, 62, 42))
    clusters = [(16, 20, 10), (24, 13, 11), (36, 16, 11), (42, 28, 10), (30, 32, 13), (16, 33, 10), (28, 41, 8)]
    if bare:
        clusters = [(15, 15, 5), (40, 14, 5), (43, 29, 4), (23, 37, 4)]
    for cx, cy, r in clusters:
        d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(17, 29, 23) if not bare else (48, 43, 28))
        d.ellipse((cx-r+1, cy-r, cx+r-2, cy+r-3), fill=(28, 43, 29) if not bare else (64, 55, 30))
        for _ in range(r * 5):
            x, y = rnd.randrange(cx-r+1, cx+r), rnd.randrange(cy-r+1, cy+r-1)
            if (x-cx)**2+(y-cy)**2 < (r-1)**2:
                color = rnd.choice([(37, 52, 31), (45, 60, 35), (24, 37, 26), (51, 61, 37)] if not bare else [(82, 66, 34), (57, 49, 28)])
                d.line((x, y, x+2, y-1), fill=color)
    return im


def bush(seed=1):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (32, 32)); d = ImageDraw.Draw(im)
    d.ellipse((4, 23, 29, 30), fill=(18, 27, 21, 180))
    for x, y, r in [(8, 20, 6), (14, 13, 8), (23, 17, 7), (19, 23, 7)]:
        d.ellipse((x-r, y-r, x+r, y+r), fill=(20, 34, 25))
        d.ellipse((x-r+2, y-r+1, x+r-1, y+r-3), fill=(33, 49, 31))
        for _ in range(18):
            xx, yy = rnd.randrange(x-r+2, x+r), rnd.randrange(y-r+2, y+r-1)
            if (xx-x)**2+(yy-y)**2 < (r-1)**2:
                d.line((xx, yy, xx+2, yy-1), fill=rnd.choice([(49, 65, 36), (27, 43, 29), (58, 67, 39)]))
    d.line((15, 29, 16, 22, 21, 20), fill=(66, 52, 33))
    return im


def fence(vertical=False, corner=False):
    im = Image.new('RGBA', (32, 32)); d = ImageDraw.Draw(im)
    if not vertical or corner:
        for x in range(-24, 48, 7):
            d.line((x, 10, x+17, 26), fill=(71, 78, 73))
            d.line((x+17, 10, x, 26), fill=(93, 96, 86))
        d.rectangle((0, 7, 31, 9), fill=(53, 60, 57)); d.line((0, 7, 31, 7), fill=(128, 129, 111))
        d.rectangle((0, 25, 31, 27), fill=(48, 54, 50)); d.line((0, 25, 31, 25), fill=(106, 110, 95))
        d.rectangle((0, 5, 3, 29), fill=(37, 43, 40)); d.line((1, 5, 1, 28), fill=(110, 113, 96))
        d.point((2, 14), fill=(124, 79, 40)); d.line((22, 7, 26, 7), fill=(112, 76, 43))
    if vertical:
        for y in range(-16, 45, 7):
            d.line((10, y, 23, y+14), fill=(78, 84, 75))
            d.line((23, y, 10, y+14), fill=(57, 65, 59))
        for x in (9, 23):
            d.line((x, 0, x, 31), fill=(105, 111, 95), width=2)
            d.line((x+2, 0, x+2, 31), fill=(36, 43, 39))
    return im


def bin_sprite(variant):
    im = Image.new('RGBA', (32, 32)); d = ImageDraw.Draw(im)
    if variant == 0:
        d.ellipse((4, 24, 29, 31), fill=(15, 21, 22, 170))
        d.polygon([(6, 9), (27, 9), (25, 28), (21, 31), (10, 30), (7, 26)], fill=(57, 74, 80), outline=(18, 27, 31))
        for x in range(9, 26, 4):
            d.line((x, 12, x, 27), fill=(23, 36, 44), width=2)
            d.line((x+1, 12, x+1, 27), fill=(98, 115, 117))
        d.ellipse((3, 4, 29, 13), fill=(34, 48, 57), outline=(16, 25, 29))
        d.polygon([(5, 8), (10, 3), (22, 2), (28, 7), (25, 10), (8, 10)], fill=(105, 121, 125), outline=(28, 42, 48))
        d.line((13, 4, 14, 1, 20, 1, 22, 4), fill=(31, 47, 55), width=2)
        d.line((8, 11, 26, 11), fill=(138, 147, 138))
        d.line((10, 28, 23, 28), fill=(111, 123, 118))
    elif variant == 1:
        d.polygon([(5, 9), (27, 9), (25, 29), (7, 29)], fill=(47, 65, 48), outline=(19, 32, 26))
        d.rectangle((4, 7, 28, 10), fill=(31, 47, 35)); d.line((5, 7, 27, 7), fill=(95, 106, 72))
        d.rectangle((8, 12, 24, 14), fill=(66, 82, 54)); d.line((8, 15, 8, 26), fill=(100, 111, 75))
        d.rectangle((12, 17, 20, 22), fill=(144, 138, 99)); d.line((13, 19, 18, 19), fill=(49, 60, 38))
        d.rectangle((7, 28, 10, 31), fill=(18, 25, 22)); d.rectangle((22, 28, 25, 31), fill=(18, 25, 22))
        d.line((16, 25, 22, 25), fill=(113, 75, 39))
    else:
        d.polygon([(4, 12), (8, 5), (22, 4), (28, 11), (26, 28), (7, 29)], fill=(70, 58, 41), outline=(22, 28, 24))
        d.polygon([(6, 9), (10, 4), (23, 5), (27, 10)], fill=(104, 83, 50), outline=(39, 39, 28))
        for y in (14, 23):
            d.line((7, y, 26, y), fill=(27, 36, 31), width=2); d.line((8, y-1, 25, y-1), fill=(133, 100, 58))
        for x,y in ((10,17),(20,12),(22,26),(8,25)):
            d.line((x,y,x+3,y+2),fill=(137,78,39))
    return im


def fire_barrel():
    im = Image.new('RGBA', (32, 56)); d = ImageDraw.Draw(im)
    d.ellipse((3, 48, 30, 55), fill=(12, 19, 18, 150))
    d.rectangle((6, 30, 26, 51), fill=(73, 55, 37), outline=(26, 31, 26))
    d.ellipse((6, 27, 26, 34), fill=(23, 26, 22), outline=(127, 79, 40))
    for y in (36, 47):
        d.line((6,y,26,y), fill=(33,39,31),width=2);d.line((7,y-1,25,y-1),fill=(132,92,48))
    d.line((9,33,9,49),fill=(108,75,42))
    for points,color in [([(9,31),(7,20),(12,23),(11,10),(16,15),(21,1),(22,17),(26,12),(24,29)],(188,80,25)),
                         ([(11,31),(10,23),(16,17),(19,7),(20,25),(24,20),(22,31)],(231,137,38)),
                         ([(14,30),(15,24),(18,18),(20,29)],(250,204,94))]:
        d.polygon(points,fill=color)
    return im


def plant(seed, fern=False):
    rnd=random.Random(seed);im=Image.new('RGBA',(32,28));d=ImageDraw.Draw(im)
    for i in range(15):
        x=rnd.randrange(5,27); top=rnd.randrange(3,20)
        d.line((16,26,x,top),fill=rnd.choice([(43,59,33),(62,73,41),(79,77,43)]))
        if fern:
            for y in range(top+4,24,4):
                xx=round(x+(16-x)*(y-top)/max(1,26-top));d.line((xx-3,y-2,xx,y,xx+3,y-3),fill=(48,67,37))
    return im


def decal(name, seed=1):
    rnd=random.Random(seed);im=Image.new('RGBA',(32,24));d=ImageDraw.Draw(im)
    if name=='puddle':
        d.polygon([(2,9),(7,4),(16,2),(27,5),(31,11),(28,19),(19,22),(6,19),(1,14)],fill=(29,42,48),outline=(48,58,57))
        d.line((7,9,15,7,24,9),fill=(75,92,97));d.line((6,16,11,17,20,17),fill=(45,63,72))
        d.line((21,13,26,13),fill=(64,78,83))
    elif name in ('paper','poster'):
        d.polygon([(5,4),(25,3),(27,17),(20,19),(17,18),(5,20)],fill=(159,152,122),outline=(68,70,55))
        for y in range(7,17,3):d.line((8,y,22-rnd.randrange(5),y),fill=(75,78,65))
        d.line((17,5,16,17),fill=(187,174,136))
    elif name=='bottles':
        for x,y,c in [(4,12,(44,69,49)),(15,8,(66,76,71)),(24,15,(87,65,41))]:
            d.rectangle((x,y,x+6,y+5),fill=c,outline=(23,37,32));d.rectangle((x+6,y+1,x+9,y+3),fill=c);d.line((x+1,y+1,x+4,y+1),fill=(114,120,98))
    elif name=='rubble':
        for _ in range(13):
            x,y=rnd.randrange(2,28),rnd.randrange(5,20);c=rnd.choice([(86,83,71),(67,70,65),(111,103,84)])
            d.polygon([(x,y),(x+4,y-2),(x+6,y+2),(x+1,y+3)],fill=c,outline=(39,43,39))
    elif name=='tire':
        d.ellipse((6,3,26,21),fill=(23,29,29),outline=(12,18,19));d.ellipse((11,7,21,17),fill=(55,57,51),outline=(72,75,64))
        for y in (5,18):d.line((11,y,20,y),fill=(54,59,54))
    elif name=='graffiti':
        d.line((4,18,11,5,18,18,25,6),fill=(107,57,43),width=2);d.line((8,19,22,19),fill=(70,43,34))
    elif name=='branch':
        d.line((3,18,26,5),fill=(73,56,36),width=2);d.line((12,13,10,5),fill=(91,73,46));d.line((20,8,27,11),fill=(91,73,46))
    elif name=='oil':
        d.ellipse((3,7,29,21),fill=(26,31,32,160));d.ellipse((8,5,20,17),fill=(31,39,41,150));d.line((8,15,16,14),fill=(56,64,62,120))
    elif name=='board':
        d.polygon([(2,17),(26,3),(29,9),(5,22)],fill=(86,68,42),outline=(35,36,28));d.line((5,17,25,6),fill=(131,101,59))
        for x,y in [(7,18),(24,6)]:d.point((x,y),fill=(158,153,121))
    return im


def road_patch(seed):
    rnd=random.Random(seed);im=Image.new('RGBA',(96,64),(58,58,62));d=ImageDraw.Draw(im)
    for _ in range(1500):
        x,y=rnd.randrange(96),rnd.randrange(64);n=rnd.choice((-5,-3,-1,1,3,5))
        d.point((x,y),fill=(58+n,58+n,62+n))
    for y in (13,49):d.line((8,y,89,y),fill=(45,46,49),width=2)
    d.ellipse((35,23,70,49),fill=(39,42,44));d.line((5,6,12,10,13,18),fill=(37,39,42))
    return im


def main():
    street_path=MAPS/'street.tmj';data=read(street_path)
    if props(data).get('city_pass_version'):
        raise SystemExit('City dressing already applied; edit the Tiled layers instead of rerunning.')
    backup=ROOT/'art_source/city_before/maps'
    for path in [*MAPS.glob('*.tmj'),*TILES.glob('*.tsj'),*TILES.glob('*.png')]:
        target=backup/path.relative_to(MAPS);target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(path,target)
    for name,im in [('tree',tree(4)),('decor_000',tree(4)),('decor_001',tree(8,True)),
                    ('bush',bush(4)),('decor_002',bush(4)),('decor_003',bush(11)),
                    ('fence',fence()),('decor_004',fence())]:png(TILES/f'{name}.png',im)
    # Upgrade the baked boundary fence without changing map GIDs or collision geometry.
    old_rows=[s for s in (ROOT/'tools/legacy/map.txt').read_text(encoding='utf-8').splitlines() if s and not s.startswith('//')]
    old_rows=[s.ljust(max(map(len,old_rows)),'#') for s in old_rows]
    original=read(ROOT/'art_source/v1/maps/street.tmj');old_ground=next(l for l in original['layers'] if l['type']=='tilelayer')
    atlas=Image.open(TILES/'world.png').convert('RGBA');grass=Image.open(TILES/'grass_0.png').convert('RGBA')
    def at(x,y):return old_rows[y][x] if 0<=y<len(old_rows) and 0<=x<len(old_rows[0]) else '#'
    for y,row in enumerate(old_rows):
        for x,ch in enumerate(row):
            if ch!='#':continue
            gid=old_ground['data'][y*old_ground['width']+x]
            im=grass.copy()
            horizontal=at(x,y-1)!='#' and at(x,y+1)!='#'
            if not horizontal:
                overlay=fence(at(x,y-1)=='#' or at(x,y+1)=='#', at(x-1,y)=='#' or at(x+1,y)=='#')
                im.alpha_composite(overlay)
            atlas.paste(im,(((gid-1)%32)*32,((gid-1)//32)*32))
    png(TILES/'world.png',atlas)

    city=[]
    def add_asset(name,im,motion=None,ground=False,collision=None,lights=None):
        png(TILES/f'city_{name}.png',im)
        tile={'id':len(city),'image':f'city_{name}.png','imagewidth':im.width,'imageheight':im.height}
        if motion:put(tile,'motion',motion)
        if ground:put(tile,'ground_detail',True)
        if collision:tile['objectgroup']={'type':'objectgroup','objects':[dict(id=1,x=collision[0],y=collision[1],width=collision[2],height=collision[3])]}
        if lights:put(tile,'lights',json.dumps(lights))
        city.append(tile);return tile['id']
    ids={}
    for i in range(3):ids[f'bin{i}']=add_asset(f'bin{i}',bin_sprite(i))
    ids['barrel']=add_asset('barrel',fire_barrel(),'fire',collision=(5,45,22,9),lights=[['flame',16,24]])
    ids['grass']=add_asset('grass',plant(4),'grass');ids['fern']=add_asset('fern',plant(9,True),'bush')
    for name in ('puddle','paper','poster','bottles','rubble','tire','graffiti','branch','oil','board'):
        ids[name]=add_asset(name,decal(name), 'paper' if name=='paper' else None, ground=name!='puddle')
    put(city[ids['puddle']],'ground','water')
    for i in range(2):
        tile=road_patch(91+i).crop((0,0,32,32));tile.alpha_composite(decal('puddle'),(0,4))
        png(TILES/f'puddle_{i}.png',tile)
    patches=[]
    for i in range(3):
        whole=road_patch(31+i)
        patches.append([add_asset(f'carbed_{i}_{j}',whole.crop(((j%3)*32,(j//3)*32,(j%3+1)*32,(j//3+1)*32)),ground=True) for j in range(6)])
    for file in ('objects.tsj','decor.tsj'):
        ts=read(TILES/file)
        for tile in ts['tiles']:
            if tile['image'] in ('bush.png','decor_002.png','decor_003.png'):put(tile,'motion','bush')
            if tile['image'] in ('house.png','shop.png'):
                foot=tile['objectgroup']['objects'][0];facade=28 if tile['image']=='house.png' else 36
                put(tile,'facade_rect',json.dumps([foot['x'],foot['y']+foot['height']-facade,foot['width'],facade]))
        save(TILES/file,ts)
    firstgid=max(r['firstgid']+read(MAPS/r['source'])['tilecount'] for r in data['tilesets'])
    data['tilesets'].append({'firstgid':firstgid,'source':'tilesets/city.tsj'})
    layers={l['name']:l for l in data['layers']};ground=next(l for l in data['layers'] if l['type']=='tilelayer')
    objects=[o for l in data['layers'] for o in l.get('objects',[])]
    ts_lookup={}
    for ref in data['tilesets'][:-1]:
        ts=read(MAPS/ref['source'])
        for tile in ts.get('tiles',[]):ts_lookup[ref['firstgid']+tile['id']]=props(tile)
    def layer(name,is_ground=False):
        if name not in layers:
            l={'id':data['nextlayerid'],'name':name,'type':'objectgroup','opacity':1,'visible':True,'draworder':'topdown','objects':[]}
            if is_ground:put(l,'ground',True)
            data['layers'].append(l);layers[name]=l;data['nextlayerid']+=1
        return layers[name]
    def graphic(name,x,bottom,layer_name='City props',is_ground=False):
        tile=city[ids[name]];obj={'id':data['nextobjectid'],'name':name,'type':'','gid':firstgid+ids[name],
             'x':x,'y':bottom,'width':tile['imagewidth'],'height':tile['imageheight'],'rotation':0,'visible':True}
        data['nextobjectid']+=1;layer(layer_name,is_ground)['objects'].append(obj);return obj
    def zone(object_class,x,y,w,h,**values):
        obj={'id':data['nextobjectid'],'name':object_class,'type':object_class,'x':x,'y':y,'width':w,'height':h,'rotation':0,'visible':True}
        for k,v in values.items():put(obj,k,v)
        data['nextobjectid']+=1;layer('City logic')['objects'].append(obj);return obj
    asphalt=next(r['firstgid']+2 for r in data['tilesets'] if r['source'].endswith('terrain.tsj'))
    grass_gid=next(r['firstgid'] for r in data['tilesets'] if r['source'].endswith('terrain.tsj'))
    for i,o in enumerate(layers.get('Vehicles',{}).get('objects',[])):
        for j in range(6):
            x=int(o['x']//32)+j%3;y=int((o['y']-o['height'])//32)+j//3
            ground['data'][y*ground['width']+x]=firstgid+patches[i%3][j]
    # Replace every old baked puddle with an editable water object and proper ground beneath it.
    water_cells=[i for i,gid in enumerate(ground['data']) if ts_lookup.get(gid,{}).get('ground')=='water']
    for i in water_cells:
        x,y=i%ground['width']*32,i//ground['width']*32
        ground['data'][i]=asphalt
        graphic('puddle',x,y+28,'Water',True)
        zone('puddle',x,y+5,32,23)
    # Garbage variations; keep all original colliders and interaction zones.
    bins=[]
    for o in objects:
        if props(o).get('kind')!='bin':continue
        x,y,w,h=o['x']+16,o['y']+16,o['width']-32,o['height']-32
        for dx in range(0,int(w),32):
            gx,gy=round((x+dx)/32),round(y/32);ground['data'][gy*ground['width']+gx]=asphalt
            bins.append((x+dx,y));graphic(f'bin{(len(bins)-1)%3}',x+dx,y+32)
    for o in objects:
        if (o.get('type') or o.get('class'))=='item' and props(o).get('item')=='pipe':
            o['x'],o['y']=1024,716
    # The front face is open to upward light; both side edges now block lateral light.
    for o in objects:
        if (o.get('type') or o.get('class'))=='light_blocker' and o.get('name','').startswith('roof_'):
            facade=36 if 'shop' in o['name'] else 28
            zone('light_facade',o['x'],o['y']+o['height'],o['width'],facade)

    # Curated clear-space props; solid objects are checked against the existing collision layer.
    collisions=[o for o in objects if (o.get('type') or o.get('class'))=='collision']
    def free(x,y,w,h):return not any(x<o['x']+o['width'] and x+w>o['x'] and y<o['y']+o['height'] and y+h>o['y'] for o in collisions)
    for x,bottom in [(560,730),(1420,668)]:
        if free(x+5,bottom-11,22,9):
            graphic('barrel',x,bottom)
            zone('spot',x-12,bottom-8,56,40,kind='barrel',approach='Здесь кто-то грелся. Огонь ещё жив.',
                 inspect=json.dumps(['Бочка тёплая. Внутри догорают обрывки писем.','Пепел мокрый, хотя огонь ещё горит.'],ensure_ascii=False))
    for name,points in {
        'paper':[(450,630),(730,590),(940,700),(1510,520),(1160,1000),(635,1010),(280,560),(1750,596)],
        'bottles':[(1020,748),(500,690),(1320,632),(820,1040)],
        'rubble':[(1770,430),(1730,558),(1710,650),(1190,720),(250,770)],
        'tire':[(1200,565),(620,790)], 'board':[(370,720),(1110,1020),(1630,610)],
        'branch':[(800,670),(440,900),(1520,1050),(214,710)],
        'oil':[(1190,610),(720,610),(1550,580)],
        'graffiti':[(830,1008),(300,276)], 'poster':[(640,1010)]}.items():
        for x,bottom in points:graphic(name,x,bottom,'Ground details',True)
    for i,(x,bottom) in enumerate([(190,420),(255,420),(1010,620),(1090,660),(1460,670),(1350,1100),(590,1065),
                                   (485,925),(390,780),(1750,710),(1830,1030),(810,340),(1345,333),(590,355),
                                   (250,850),(1130,750),(1480,950),(1570,850),(550,1120),(880,1120)]):
        graphic('fern' if i%4==0 else 'grass',x,bottom)
    put(data,'city_pass_version',1)
    save(TILES/'city.tsj',{'type':'tileset','version':'1.10','name':'Abandoned city','columns':0,
                          'tilewidth':max(t['imagewidth'] for t in city),'tileheight':max(t['imageheight'] for t in city),
                          'objectalignment':'bottomleft','tilecount':len(city),'tiles':city})
    save(street_path,data)
    print(f'City: {len(city)} reusable assets, {len(water_cells)} reactive puddles, {len(bins)} varied bins, pipe moved to bins.')


if __name__=='__main__':main()

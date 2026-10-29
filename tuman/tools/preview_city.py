"""Render the dressed map and reactive water using the actual game systems."""
import math
import os
from pathlib import Path
import sys
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image
from characters import Player,build_hero_frames,build_monster_frames
from locations import build_locations
from rendering import WorldCanvas,LensEffects,hd_effect
from settings import DIFFICULTIES,GAME_W,GAME_H
from world import make_glow

ROOT=Path(__file__).resolve().parents[1]


def render(loc,player,t,camera,dt,fog=False,lens=None):
    canvas=WorldCanvas((GAME_W,GAME_H));canvas.fill((8,8,10))
    cx,cy=camera;canvas.blit(loc.map_surf,(-cx,-cy))
    for _,im,x,y in loc.ground_scenery.props_at(t):canvas.blit(im,(x-cx,y-cy))
    loc.water.update(dt,player.rect.center,player.stepped);loc.water.draw(canvas,camera)
    queue=[(z,(im,x,y)) for z,im,x,y in loc.scenery.props_at(t)]
    queue.append((player.rect.bottom,player))
    for _,thing in sorted(queue,key=lambda p:p[0]):
        if isinstance(thing,tuple):im,x,y=thing;canvas.blit(im,(x-cx,y-cy))
        else:thing.draw(canvas,cx,cy)
    for pipe in loc.pipe_rects:
        from world import draw_pipe_item
        draw_pipe_item(canvas,pipe.move(-cx,-cy))
    if fog:
        loc.lighting.draw(canvas,loc.fog,player.flashlight_origin(),player.rect.center,player.facing,camera,loc.light_blockers)
        for kind,x,y in loc.glows:
            if kind=='flame':
                glow=hd_effect(make_glow(42,(120,58,17)))
                glow.set_alpha(round(220+25*math.sin(t*11+x)))
                canvas.blit(glow,(x-42-cx,y-42-cy),special_flags=pygame.BLEND_RGB_ADD)
    if lens:lens.apply(canvas.surface,camera,loc.name,1,dt)
    return canvas.surface


def main():
    pygame.init();pygame.display.set_mode((1,1))
    loc=build_locations(build_monster_frames(),DIFFICULTIES['normal'])['street']
    player=Player((400,386),build_hero_frames());player.left_hand='flashlight';player.right_hand='pipe';player.light_on=True
    water=min(loc.puddles,key=lambda r:pygame.Vector2(r.center).distance_to((400,386)))
    camera=(max(0,min(704,water.centerx-160)),max(0,min(396,water.centery-110)))
    lens=LensEffects();images=[]
    for i in range(36):
        t=i/12;player.visual_time=t;player.moving=True;player.walk_time=t;player.facing='down'
        player.rect.center=(water.centerx+round(math.sin(t*1.8)*3),water.centery)
        player.stepped=i%3==0
        surface=render(loc,player,t,camera,1/12,lens=lens)
        images.append(Image.frombytes('RGB',surface.get_size(),pygame.image.tobytes(surface,'RGB')))
    images[0].save(ROOT/'art_source/city-water.gif',save_all=True,append_images=images[1:],duration=83,loop=0,disposal=2)
    preview=pygame.Surface((1280,400));preview.fill((20,22,25));font=pygame.font.SysFont('arial',18)
    player.rect.center=(470,366);player.facing='right';player.moving=False;player.stepped=False
    for i,fog in enumerate((False,True)):
        preview.blit(render(loc,player,1.2,(240,240),0,fog=fog,lens=LensEffects()),(i*640,40))
        preview.blit(font.render('City details / bins, barrel fire and relocated pipe' if not fog else 'Gameplay light and subtle lens softness',True,(210,210,190)),(i*640+12,10))
    pygame.image.save(preview,str(ROOT/'art_source/city-preview.png'))
    pygame.quit();print(ROOT/'art_source/city-preview.png')


if __name__=='__main__':main()

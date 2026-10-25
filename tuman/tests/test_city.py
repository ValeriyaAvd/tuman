"""Regression checks for lateral facade light, reactive water and corpse layering."""
import os
import json
import tempfile
from pathlib import Path
import sys
import unittest
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from characters import Player, Monster, build_monster_frames
from environment import WaterSystem
from lighting import facade_edges
from locations import LocationStore
from rendering import WorldCanvas, LensEffects, draw_ground_corpses
from settings import DIFFICULTIES, ART_SCALE
from atmosphere import foliage_frame
from tiled_map import TiledMap
from settings import DATA_DIR


class CityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((1,1))
        cls.monsters=build_monster_frames()
        cls.store=LocationStore(cls.monsters,DIFFICULTIES['normal'])

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_facade_blocks_light_from_sides_but_accepts_front_light(self):
        lighting=self.store['street'].lighting
        roof=pygame.Rect(80,60,40,30);face=pygame.Rect(80,90,40,10)
        blockers=[roof]+facade_edges(face)
        for origin,facing in [((60,95),'right'),((140,95),'left')]:
            visible,_=lighting.masks(origin,facing,blockers)
            x,y=(round((point-origin[i]+120)*ART_SCALE) for i,point in enumerate((100,95)))
            self.assertEqual(visible.get_at((x,y))[:3],(0,0,0))
        origin=(100,125)
        visible,_=lighting.masks(origin,'up',blockers)
        self.assertEqual(visible.get_at((120*ART_SCALE,90*ART_SCALE))[:3],(255,255,255))

    def test_water_responds_only_to_wet_footsteps_and_ripples_expire(self):
        water=WaterSystem([pygame.Rect(10,10,20,10)])
        water.update(.016,(2,2),True);self.assertEqual(water.ripples,[])
        water.update(.016,(20,15),False);self.assertEqual(water.ripples,[])
        water.update(.016,(20,15),True);self.assertEqual(len(water.ripples),1)
        water.update(.016,(20,15),True);self.assertEqual(len(water.ripples),1)
        canvas=WorldCanvas((40,30));canvas.fill((25,35,40))
        before=pygame.image.tobytes(canvas.surface,'RGB');water.draw(canvas,(0,0))
        self.assertNotEqual(before,pygame.image.tobytes(canvas.surface,'RGB'))
        water.update(1,(2,2),False);self.assertEqual(water.ripples,[])

    def test_water_painted_in_tiled_creates_reactive_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'painted.tmj'
            path.write_text(json.dumps({'type':'map','orientation':'orthogonal','width':1,'height':1,
                'tilewidth':32,'tileheight':32,'infinite':False,
                'tilesets':[{'firstgid':1,'source':str(Path(DATA_DIR)/'maps/tilesets/terrain.tsj')}],
                'layers':[{'type':'tilelayer','name':'Water','width':1,'height':1,'data':[9]}]}),encoding='utf-8')
            tiled=TiledMap(path)
            self.assertEqual(tiled.puddles,[pygame.Rect(0,0,16,16)])
            water=WaterSystem(tiled.puddles);water.update(.016,(8,8),True)
            self.assertEqual(len(water.ripples),1)

    def test_corpses_stay_below_player_when_approached_from_either_side(self):
        green=(20,180,50);red=(200,20,20)
        frame=pygame.Surface((24,38),pygame.SRCALPHA);frame.fill(green)
        frames={d:{'stand':frame,'idle':[frame,frame],'walk':[frame]*4} for d in ('up','down','right','left')}
        monster_frames=dict(self.monsters);monster_frames['corpse']=pygame.Surface((40,24),pygame.SRCALPHA)
        monster_frames['corpse'].fill(red)
        monster=Monster((20,22),monster_frames);monster.dead=True
        for y in (18,24):
            with self.subTest(player_y=y):
                canvas=WorldCanvas((40,40));canvas.fill((0,0,0));player=Player((20,y),frames)
                living=draw_ground_corpses(canvas,[monster],(0,0),pygame.Rect(0,0,40,40))
                self.assertEqual(living,[])
                player.draw(canvas,0,0)
                sample=(24*ART_SCALE,min(player.rect.bottom-2,26)*ART_SCALE)
                self.assertEqual(canvas.surface.get_at(sample)[:3],green)

    def test_lens_history_is_cleared_on_teleport_and_motion_does_not_accumulate(self):
        lens=LensEffects(softness=0,motion=.12)
        a=pygame.Surface((80,40));a.fill((200,0,0));lens.apply(a,(0,0),'street',0,1/60)
        b=pygame.Surface((80,40));b.fill((0,0,200));lens.apply(b,(1,0),'street',1,1/60)
        self.assertGreater(b.get_at((30,20)).r,0)
        c=pygame.Surface((80,40));c.fill((0,200,0));lens.apply(c,(1,0),'shop',1,1/60)
        self.assertEqual(c.get_at((30,20))[:3],(0,200,0))

    def test_city_content_is_reachable_and_vegetation_roots_do_not_move(self):
        loc=self.store['street']
        self.assertGreaterEqual(len(loc.puddles),6)
        self.assertTrue(any(g[0]=='flame' for g in loc.glows))
        pipe=loc.pipe_rects[0]
        bins=[s for s in loc.spots if s.kind=='bin']
        self.assertLess(min(pygame.Vector2(pipe.center).distance_to(s.zone.center) for s in bins),45)
        self.assertFalse(any(pipe.colliderect(w) for w in loc.walls))
        index=next(i for i,k in loc.scenery.effects.items() if k=='bush')
        image=loc.props[index][1]
        frame=foliage_frame(image,1.4,'bush')
        bottom=pygame.Rect(0,image.get_height()-3,image.get_width(),3)
        self.assertEqual(pygame.image.tobytes(image.subsurface(bottom),'RGBA'),
                         pygame.image.tobytes(frame.subsurface(bottom),'RGBA'))


if __name__=='__main__':unittest.main()

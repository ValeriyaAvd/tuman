# =====================================================
#  Туман — прототип хоррор-игры
#  Нужно: Python + pygame-ce   (pip install pygame-ce)
#  Запуск: python main.py
#
#  Управление: WASD или стрелки — ходить, Shift — бежать, Пробел — удар (когда есть оружие)
#              E — осмотреть / прочитать записку / закрыть
#              F — включить / выключить фонарик (сначала найди его)
#              R — начать заново (после смерти)
#              Пробел — пропустить вступление
#              Esc — выход
#
#  Файлы игры:
#    main.py       — запуск и главный цикл (этот файл)
#    settings.py   — все настройки (числа, громкость)
#    texts.py      — все тексты и сценарий вступления
#    world.py      — карта, дома, туман, свет, фонарик
#    characters.py — герой и монстры
#    sounds.py     — звуки и музыка (загружает файлы из data/sounds)
#    story.py      — вступление и осмотр предметов
#    ui.py         — мысли героя, подсказки, записка, инвентарь
#    locations.py  — обнаружение и ленивая загрузка локаций
#    tiled_map.py  — чтение карт Tiled JSON (.tmj) и тайлсетов (.tsj)
#    lighting.py   — тени от луча фонарика
#    atmosphere.py — мигание фонарей, качание деревьев, VHS-помехи
#    environment.py — лужи с рябью, летящие листья
#    rendering.py  — холст мира, размытие, тела на земле
#    data/maps/    — карты, проект Tiled и тайлсеты
#    data/         — картинки (hero.png, monster.png, exclaim.png)
#    data/sounds/  — все звуки (.wav / .ogg)
#    tools/        — проверка карт, превью и генерация звуков (игре не нужны)
# =====================================================

import sys
import math
import random
import pygame
from settings import *
from texts import *
from world import *
from characters import *
from sounds import *
from story import *
from ui import *
from locations import *
from rendering import WorldCanvas, hd_effect, LensEffects, draw_ground_corpses
from atmosphere import TapeDistortion
from environment import DriftingLeaves


# ---------- ОКНО ИГРЫ ----------
def make_display(fullscreen):
    """Создаёт настоящее окно: на весь экран или обычное окно 960x540."""
    if fullscreen:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)   # (0, 0) — "размер моего экрана"
    return pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)  # окно можно тянуть мышкой


def present(window, display, scene=None):
    """Растягивает холст на всё окно, сохраняя пропорции (по краям — чёрные полосы)."""
    dw, dh = display.get_size()
    if PIXEL_PERFECT:
        # Увеличиваем только в ЦЕЛОЕ число раз (считаем по пикселям игры) —
        # тогда каждый пиксель игры становится одинаковым квадратиком, без "кривизны"
        base_w, base_h = scene.get_size() if scene is not None else (GAME_W, GAME_H)
        k = max(1, int(min(dw / base_w, dh / base_h)))
        w, h = base_w * k, base_h * k
    else:
        scale = min(dw / WIN_W, dh / WIN_H)      # во сколько раз можно увеличить, чтобы влезло
        w, h = int(WIN_W * scale), int(WIN_H * scale)
    display.fill((0, 0, 0))
    if scene is not None:
        display.blit(pygame.transform.scale(scene, (w, h)), ((dw - w) // 2, (dh - h) // 2))
    display.blit(pygame.transform.scale(window, (w, h)), ((dw - w) // 2, (dh - h) // 2))
    pygame.display.flip()

# ---------- МЕНЮ ВЫБОРА СЛОЖНОСТИ ----------
def difficulty_menu(display, fullscreen, window, clock, big_font, font, small_font):
    """Показывает меню, пока игрок не выберет сложность.
    Возвращает (ключ сложности, окно, полный ли экран) — окно могло поменяться от F11."""
    keys = list(DIFFICULTIES)                   # ["easy", "normal", "hard"]
    choice = keys.index(DEFAULT_DIFFICULTY)     # какой пункт сейчас выбран
    t = 0.0
    while True:
        t += clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key == pygame.K_F11:
                fullscreen = not fullscreen
                display = make_display(fullscreen)
            if event.key in (pygame.K_w, pygame.K_UP):
                choice = (choice - 1) % len(keys)      # % — чтобы с верхнего пункта перейти на нижний
            if event.key in (pygame.K_s, pygame.K_DOWN):
                choice = (choice + 1) % len(keys)
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                return keys[choice], display, fullscreen

        window.fill((12, 12, 15))
        draw_text(window, big_font, "ТУМАН", (WIN_W // 2, 120), color=(200, 196, 188), center=True)
        draw_text(window, font, "Выбери сложность", (WIN_W // 2, 200), color=(150, 148, 144), center=True)
        for i, key in enumerate(keys):
            y = 260 + i * 50
            if i == choice:
                # Выбранный пункт — светлее и слегка "дышит"
                glow = 210 + int(25 * math.sin(t * 4))
                draw_text(window, font, "›  " + DIFFICULTIES[key]["name"] + "  ‹", (WIN_W // 2, y),
                          color=(glow, glow - 14, glow - 34), center=True)
            else:
                draw_text(window, font, DIFFICULTIES[key]["name"], (WIN_W // 2, y),
                          color=(100, 100, 106), center=True)
        draw_text(window, small_font, DIFFICULTIES[keys[choice]]["about"], (WIN_W // 2, 420),
                  color=(150, 140, 130), center=True)
        draw_text(window, small_font, "W / S — выбор      Enter — начать", (WIN_W // 2, WIN_H - 40),
                  color=(90, 90, 96), center=True)
        present(window, display)

# ---------- ГЛАВНЫЙ ЦИКЛ ----------
def main():
    # Настройки звука нужно задать ДО pygame.init():
    # 22050 — частота (сколько чисел в секунде звука), -16 — 16-битные числа, 1 — моно
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    fullscreen = FULLSCREEN
    display = make_display(fullscreen)          # настоящее окно на экране
    window = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)  # UI overlay, separate from native-resolution world.
    pygame.display.set_caption("Туман — прототип")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 22)
    thought_font = pygame.font.SysFont("arial", 22, italic=True)   # мысли героя — курсивом
    note_font = pygame.font.SysFont("georgia", 26, italic=True)     # "почерк" на записке
    big_font = pygame.font.SysFont("arial", 60, bold=True)
    intro_font = pygame.font.SysFont("arial", 26, italic=True)
    small_font = pygame.font.SysFont("arial", 18)

    game = WorldCanvas((GAME_W, GAME_H))
    tape = TapeDistortion(game.surface.get_size())
    lens = LensEffects()
    leaves = DriftingLeaves((GAME_W, GAME_H))

    # Меню сложности — в самом начале
    if SKIP_MENU:
        level = DEFAULT_DIFFICULTY
    else:
        level, display, fullscreen = difficulty_menu(display, fullscreen, window, clock,
                                                     big_font, font, small_font)
    difficulty = DIFFICULTIES[level]

    monster_frames = build_monster_frames()
    locations = build_locations(monster_frames, difficulty)
    loc = locations[locations.start_name]
    exclaim_img = load_image("exclaim.png")
    vignette = hd_effect(make_vignette())
    fog_clouds = hd_effect(load_image("fog_clouds.png"))   # клочья тумана, которые медленно плывут
    fog_clouds.set_alpha(FOG_CLOUDS_ALPHA)   
    car = loc.car_rects[0] if loc.car_rects else pygame.Rect(*loc.start, TILE, TILE)
    door_pos = (car.centerx - 4, car.bottom + 3) if loc.car_rects else loc.start
    hero_frames = build_hero_frames()
    player = Player(door_pos, hero_frames, difficulty["hero_hp"])
    player.facing = "down"
    sounds = SoundSystem()

    # Свечение, которое видно даже сквозь туман
    lamp_glow = hd_effect(make_glow(34, (96, 84, 52)))
    glow_images = {
        "lamp": lamp_glow,
        "lamp_broken": lamp_glow,
        "window": hd_effect(make_glow(14, (70, 52, 24))),
        "booth": hd_effect(make_glow(14, (60, 58, 46))),
        "fridge": hd_effect(make_glow(22, (34, 54, 64))),
        "flame": hd_effect(make_glow(42, (120, 58, 17))),
        "desk": hd_effect(make_glow(9, (110, 92, 50))),     # само свечение абажура
    }
    desk_cone, desk_center = make_desk_cone()
    desk_cone = hd_effect(desk_cone)

    reading = False      # открыта ли записка
    inventory = []                  # подобранные предметы (по порядку): "flashlight", "pipe", "note"...
    inventory_open = False          # открыт ли инвентарь (игра на паузе)
    inv_choice = 0                  # какая клеточка инвентаря выбрана
    reading_from_inventory = False  # записку открыли из инвентаря — после неё вернуться туда
    picture = None                  # какая картинка сейчас открыта на весь экран (None — никакая)
    picture_next = None             # картинка, которую откроет следующее нажатие E
    picture_spot = None             # у какого места эта картинка (открыть её можно только там)
    picture_guard = 0.0             # первые полсекунды картинку нельзя закрыть (чтобы не закрыть случайно)
    flags = set()                   # сюжетные флаги: открытый сейф и т. п. (для show_if / hide_if в Tiled)
    code_spot = None                # у какого замка сейчас открыто окно ввода кода
    code_digits = ""                # что уже набрано
    code_error = 0.0                # сколько ещё подсвечивать неверный код
    found_item = None               # какой предмет только что нашли (иконка на экране)
    found_timer = 0.0               # сколько ещё показывать иконку находки
    item_icons = load_item_icons()   
    time_total = 0.0
    broken_on = True     # горит ли сейчас сломанный фонарь
    dead = False         # погиб ли герой
    dead_timer = 0.0     # сколько секунд прошло после смерти
    radio = 0.0          # сила помех радио: 0 — тихо, 1 — монстр вплотную
    has_flashlight = False   # нашёл ли герой фонарик
    dark_warned = set()      # в каких помещениях герой уже пожаловался, что темно без фонарика
    flash_on = False         # включён ли он
    thought = INTRO_THOUGHT  # мысль героя внизу экрана
    thought_timer = 0.0
    intro = Intro()
    hero_visible = False     # пока герой в машине, его не видно
    focus_blend = 0.0        # камера: 0 — смотрит на машину, 1 — на героя
    if SKIP_INTRO or not loc.car_rects:
        intro.phase = "done"
        hero_visible = True
        focus_blend = 1.0
        thought_timer = thought_time(thought)
    seen_monster = False     # видел ли герой монстра хоть раз
    freeze_timer = 0.0       # сколько ещё секунд герой стоит в оцепенении
    exclaim_timer = 0.0      # сколько ещё показывать "!" над головой
    shake_timer = 0.0        # сколько ещё трясётся камера
    hurt_flash = 0.0         # красная вспышка, когда монстр ранил героя (1 — ярко, 0 — нет)   
    fear = 0.0               # страх: 0 — спокойно, 1 — монстр вплотную
    heart_timer = 0.0        # через сколько секунд следующий удар сердца
    heart_pulse = 0.0        # вспышка тёмных краёв в такт сердцу
    line_cooldown = 0.0      # чтобы герой не повторял реплики про монстра слишком часто
    hint = ""                # подсказка по управлению (под мыслью)
    door_fade = 0.0          # затемнение при переходе через дверь: 1 — чёрный экран, 0 — нет
    has_weapon = False       # подобрал ли герой трубу
    swing_timer = 0.0        # сколько ещё длится замах (0 — сейчас не бьёт)
    attack_cooldown = 0.0    # через сколько секунд можно ударить снова
    hit_done = True          # уже проверили, попал ли этот удар
    kills = 0                # сколько монстров убито
    hint_timer = 0.0

    while True:
        dt = clock.tick(FPS) / 1000      # сколько секунд прошло с прошлого кадра
        time_total += dt

        # --- 1. События (нажатия клавиш, закрытие окна) ---
        playing = intro.phase == "done"     # вступление закончилось — можно управлять героем
        near_note = playing and loc.note_rect is not None and player.rect.inflate(26, 26).colliderect(loc.note_rect)
        near_car = playing and not has_flashlight and any(player.rect.inflate(20, 20).colliderect(c) for c in loc.car_rects)
        near_pipe = playing and not has_weapon and any(player.rect.inflate(20, 20).colliderect(p) for p in loc.pipe_rects)
        # Рядом с дверью?
        near_door = None
        if playing and not dead:
            for door in loc.doors:
                if player.rect.colliderect(door.zone):
                    near_door = door
        # Что можно осмотреть прямо сейчас (если рядом нет записки, машины с фонариком и двери)
        near_spot = None
        if playing and not near_note and not near_car and not near_door and not near_pipe and not dead:
            for spot in loc.spots:
                if spot.kind == "my_car" and not has_flashlight:
                    continue
                if player.rect.colliderect(spot.zone):
                    near_spot = spot
                    break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                fullscreen = not fullscreen
                display = make_display(fullscreen)     # F11 — полный экран / окно
                continue
            if event.type == pygame.KEYDOWN and not playing:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    # Пропустить вступление: герой сразу стоит у машины
                    intro.phase = "done"
                    sounds.engine_off()
                    hero_visible = True
                    focus_blend = 1.0
                    thought = INTRO_THOUGHT
                    thought_timer = thought_time(thought)
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                continue                        # остальные клавиши во вступлении не работают
            if event.type == pygame.KEYDOWN:
                # --- Картинка на весь экран: закрывается E, Esc или пробелом ---
                if picture:
                    if event.key in (pygame.K_e, pygame.K_ESCAPE, pygame.K_SPACE) and picture_guard <= 0:
                        picture = None
                    continue
                # --- Кодовый замок: цифры, Backspace, Esc ---
                if code_spot:
                    digit = event.unicode if event.unicode.isdigit() else None
                    if event.key == pygame.K_ESCAPE:
                        code_spot = None
                    elif event.key == pygame.K_BACKSPACE:
                        code_digits = code_digits[:-1]
                    elif digit and len(code_digits) < len(code_spot.code):
                        code_digits += digit
                        sounds.switch()
                        if len(code_digits) == len(code_spot.code):
                            if code_digits == code_spot.code:
                                spot = code_spot
                                code_spot = None
                                spot.solved = True
                                if spot.flag:
                                    flags.add(spot.flag)
                                if spot.gives:
                                    inventory.append(spot.gives)
                                    found_item, found_timer = spot.gives, FOUND_TIME
                                    hint = KEY_TAKEN_HINT
                                    hint_timer = 5.0
                                sounds.pickup()
                                spot.inspect = spot.opened_lines or spot.inspect
                                spot.times = 0
                                thought = spot.next_text()
                                thought_timer = thought_time(thought)
                            else:
                                code_digits = ""
                                code_error = 0.8
                                sounds.hit()
                                thought = CODE_WRONG
                                thought_timer = thought_time(thought)
                    continue
                # --- Инвентарь: пока он открыт, клавиши работают только в нём ---
                if inventory_open:
                    if event.key in (pygame.K_i, pygame.K_TAB, pygame.K_ESCAPE):
                        inventory_open = False
                    elif event.key in (pygame.K_a, pygame.K_LEFT) and inventory:
                        inv_choice = (inv_choice - 1) % len(inventory)
                    elif event.key in (pygame.K_d, pygame.K_RIGHT) and inventory:
                        inv_choice = (inv_choice + 1) % len(inventory)
                    elif event.key == pygame.K_e and inventory and inventory[inv_choice] == "note":
                        inventory_open = False         # перечитать записку
                        reading = True
                        reading_from_inventory = True
                        sounds.note()
                    elif event.key == pygame.K_e and inventory and "use" in ITEMS.get(inventory[inv_choice], {}):
                        # Применить предмет к тому, что рядом (отмычки к двери, ключ к воротам)
                        inventory_open = False
                        item = inventory[inv_choice]
                        if near_door and near_door.locked and near_door.requires == item:
                            near_door.locked = False
                            sounds.hit()
                            thought = near_door.unlock_text or "Открыто."
                        elif near_spot and near_spot.requires == item and not near_spot.solved:
                            near_spot.solved = True
                            if near_spot.flag:
                                flags.add(near_spot.flag)
                            sounds.hit()
                            near_spot.inspect = near_spot.opened_lines
                            near_spot.times = 0
                            thought = near_spot.next_text()
                        elif (near_door and near_door.locked) or (near_spot and near_spot.requires and not near_spot.solved):
                            thought = USE_WRONG
                        else:
                            thought = USE_NOTHING
                        thought_timer = thought_time(thought)
                    continue                           # остальное в игре сейчас не обрабатываем
                if event.key in (pygame.K_i, pygame.K_TAB) and not reading and not dead:
                    inventory_open = True
                    inv_choice = min(inv_choice, max(0, len(inventory) - 1))
                    continue

                # --- Записка открыта: E или Esc закрывают её ---
                if reading:
                    if event.key in (pygame.K_e, pygame.K_ESCAPE):
                        reading = False
                        if reading_from_inventory:     # читали из инвентаря — возвращаемся туда
                            reading_from_inventory = False
                            inventory_open = True
                        else:
                            thought = NOTE_THOUGHT     # мысли героя — уже после записки
                            thought_timer = thought_time(thought)
                            hint = NOTE_TAKEN_HINT
                            hint_timer = 5.0
                    continue                           # пока читаем, остальные клавиши не работают

                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r and dead:
                    # Начать заново: герой возвращается на улицу, монстры — на свои места
                    loc = locations[locations.start_name]
                    player = Player(loc.start, hero_frames, difficulty["hero_hp"])
                    for place in locations.loaded.values():
                        for m in place.monsters:
                            m.reset()
                    dead = False
                    dead_timer = 0.0
                    freeze_timer = exclaim_timer = shake_timer = fear = hurt_flash = 0.0
                if event.key == pygame.K_e and not dead:
                    if near_door and near_door.locked:
                        # Сама дверь не открывается: нужный предмет игрок применяет из инвентаря
                        if near_door.try_flag:
                            flags.add(near_door.try_flag)
                        lines = near_door.locked_lines
                        thought = lines[min(near_door.tries, len(lines) - 1)]
                        near_door.tries += 1
                        thought_timer = thought_time(thought)
                    elif near_door:
                        # Переход в другую локацию
                        sounds.car("door_open")
                        loc, arrival = locations.enter(near_door)
                        old_player = player            # здоровье переносим в новую локацию
                        player = Player(arrival, hero_frames, old_player.max_hp)
                        player.hp = old_player.hp
                        player.facing = near_door.facing
                        # Cached locations retain monster and story state between visits.
                        door_fade = 1.0
                        if loc.inside and not has_flashlight and loc.name not in dark_warned:
                            dark_warned.add(loc.name)  # в каждом помещении — только при первом входе
                            thought = DARK_INSIDE_THOUGHT
                            thought_timer = thought_time(thought)
                    elif near_pipe:
                        has_weapon = True              # теперь герой может отбиваться
                        inventory.append("pipe")                        
                        sounds.pickup()
                        thought = PIPE_THOUGHT_AFTER_MONSTER if seen_monster else PIPE_THOUGHT
                        thought_timer = thought_time(thought)
                        hint = PIPE_HINT
                        hint_timer = 6.0
                    elif near_note:
                        reading = True
                        sounds.note()
                        loc.note_rect = None           # записка исчезает с земли...
                        inventory.append("note")       # ...и попадает в инвентарь
                    elif near_car:
                        has_flashlight = True
                        inventory.append("flashlight")                        
                        sounds.switch()
                        thought = FLASHLIGHT_THOUGHT
                        thought_timer = thought_time(thought)
                        hint = "[F] — включить / выключить фонарик"
                        hint_timer = 6.0
                    elif near_spot and picture_next and near_spot is picture_spot:
                        # Фраза уже сказана — следующее нажатие E открывает картинку
                        picture = picture_next
                        picture_next = None
                        picture_guard = 0.3
                        thought_timer = 0              # фразу прячем — сейчас смотрим на рисунок
                        sounds.note()
                    elif near_spot and near_spot.code and not near_spot.solved:
                        code_spot = near_spot           # открываем окно ввода кода
                        code_digits = ""
                        sounds.switch()
                    elif (near_spot and near_spot.gives and not near_spot.code and not near_spot.requires
                          and not near_spot.solved and (not near_spot.gives_if or near_spot.gives_if in flags)):
                        near_spot.solved = True         # нашли предмет при осмотре
                        inventory.append(near_spot.gives)
                        sounds.pickup()
                        found_item, found_timer = near_spot.gives, FOUND_TIME
                        hint = ITEM_TAKEN_HINT.format(ITEMS[near_spot.gives]["name"])
                        hint_timer = 5.0
                        thought = near_spot.found or near_spot.next_text()
                        thought_timer = thought_time(thought)
                    elif near_spot:
                        thought = near_spot.next_text()
                        thought_timer = thought_time(thought)
                        # Если к этой фразе привязана картинка — её откроет следующее нажатие E
                        index = min(near_spot.times, len(near_spot.inspect)) - 1
                        picture_next = SPOT_PICTURES.get((near_spot.kind, index))
                        picture_spot = near_spot
                if event.key == pygame.K_SPACE and has_weapon and not dead and attack_cooldown <= 0:
                    swing_timer = SWING_TIME           # начинаем замах
                    attack_cooldown = ATTACK_COOLDOWN
                    hit_done = False
                    sounds.swing()
                elif event.key == pygame.K_SPACE and not has_weapon and playing and not dead and thought_timer < 0.5 \
                        and any(not m.dead and math.dist(m.rect.center, player.rect.center) < FEAR_RANGE for m in loc.monsters):
                    thought = NO_WEAPON_THOUGHT        # монстр рядом, а ударить нечем
                    thought_timer = thought_time(thought)
                if event.key == pygame.K_f and has_flashlight and not dead:
                    flash_on = not flash_on
                    sounds.switch()

        # Данные текущей локации — под короткими именами. Берём их после событий:
        # если в этом кадре герой прошёл через дверь (или начал заново), локация уже другая
        rows, walls, note_rect = loc.rows, loc.walls, loc.note_rect
        map_surf, glows = loc.map_surf, loc.glows
        map_w, map_h = (v // ART_SCALE for v in map_surf.get_size())
        fog, flashlight = loc.fog, loc.flashlight
        spots, remarks, monsters = loc.spots, loc.remarks, loc.monsters

        # --- 2. Логика ---
        if not playing:
            for event_name in intro.update(dt):
                if event_name == "hero_out":
                    hero_visible = True
                    focus_blend = 0.0
                elif event_name == "control":
                    thought = INTRO_THOUGHT
                    thought_timer = thought_time(thought)
                elif event_name == "stall":
                    sounds.car("stall")
                    sounds.engine_off()
                else:
                    sounds.car(event_name)     # кашель мотора, двери
            sounds.engine(intro.engine_level())
        elif dead:
            dead_timer += dt
        elif not reading and not inventory_open and not picture and not code_spot:     # записка или инвентарь — игра на паузе
            # Герой сам говорит, когда впервые подходит к чему-то интересному.
            # Только если сейчас он ничего не говорит — чтобы фразы не перебивали друг друга.
            if thought_timer < 0.5:
                for spot in spots:
                    if not spot.approach_said and player.rect.colliderect(spot.approach_zone):
                        spot.approach_said = True
                        thought = spot.approach
                        thought_timer = thought_time(thought)
                        break
                else:
                    for remark in remarks:
                        if not remark[2] and player.rect.colliderect(remark[0]):
                            remark[2] = True
                            thought = remark[1]
                            thought_timer = thought_time(thought)
                            break

            if freeze_timer > 0:
                freeze_timer -= dt                 # герой замер от ужаса — управлять нельзя
                player.moving = False
                player.stepped = False
                player.walk_time = 0.0
            else:
                player.update(dt, pygame.key.get_pressed(), walls)
            if player.stepped:
                # На какой клетке стоит герой — от этого зависит звук шага
                tile = rows[player.rect.centery // TILE][player.rect.centerx // TILE]
                if loc.water.at(player.rect.center) is not None or tile == "~":
                    sounds.footstep("water")
                elif tile in GRASS_TILES:
                    sounds.footstep("soft")
                else:
                    sounds.footstep("hard")

            # Удар трубой: попадание проверяем один раз — в середине замаха
            attack_cooldown -= dt
            if swing_timer > 0:
                swing_timer -= dt
                if not hit_done and swing_timer <= SWING_TIME / 2:
                    hit_done = True
                    hitbox = attack_hitbox(player)
                    for m in monsters:
                        if not m.dead and hitbox.colliderect(monster_body(m)):
                            sounds.hit()
                            shake_timer = max(shake_timer, 0.12)
                            if m.hit(player.rect.centerx, player.rect.centery, walls):
                                sounds.monster_death()
                                kills += 1
                                thought = FIRST_KILL_THOUGHT if kills == 1 else random.choice(KILL_THOUGHTS)
                                thought_timer = thought_time(thought)

            nearest = None
            line_cooldown -= dt
            for m in monsters:
                see = MONSTER_SEE_LIGHT if flash_on else MONSTER_SEE
                was_chasing = m.chasing
                dist, noticed = m.update(dt, player, walls, see)

                # Первая встреча: герой замирает, поворачивается, "!" и удар
                if not seen_monster and monster_in_view(m, player, flash_on, loc.fog_full):
                    seen_monster = True
                    face_towards(player, m.rect.centerx, m.rect.centery)
                    freeze_timer = 0.7
                    exclaim_timer = 1.3
                    shake_timer = 0.35
                    line_cooldown = 6.0
                    # Без трубы герой понимает, что ему нечем отбиваться
                    thought = FIRST_SIGHT_THOUGHT if has_weapon else FIRST_SIGHT_UNARMED_THOUGHT
                    thought_timer = thought_time(thought)
                    sounds.shock()

                if noticed:
                    pan = max(-1.0, min(1.0, (m.rect.centerx - player.rect.centerx) / 80))
                    sounds.growl(pan)
                    exclaim_timer = max(exclaim_timer, 0.9)
                    if line_cooldown <= 0:
                        thought = random.choice(NOTICED_THOUGHTS)
                        thought_timer = thought_time(thought)
                        line_cooldown = 15.0
                elif was_chasing and not m.chasing and line_cooldown <= 5:
                    # Монстр потерял героя — оторвались
                    thought = random.choice(ESCAPED_THOUGHTS)
                    thought_timer = thought_time(thought)
                    line_cooldown = 15.0

                if nearest is None or dist < nearest:
                    nearest = dist
                if m.harmful() and player.hurt <= 0 and player.rect.colliderect(m.rect.inflate(4, 4)):   # догнал!
                    player.hp -= 1
                    if player.hp <= 0:
                        dead = True
                        sounds.scare()
                    else:
                        # Ранен, но жив: героя отбрасывает, монстр на миг замирает
                        player.hurt = HURT_TIME
                        player.knockback(m.rect.centerx, m.rect.centery, walls)
                        m.stun = 0.5
                        sounds.shock()
                        shake_timer = max(shake_timer, 0.25)
                        hurt_flash = 1.0

            # Радио шипит тем сильнее, чем ближе монстр
            if nearest is not None and nearest < RADIO_RANGE:
                radio = (1 - nearest / RADIO_RANGE) ** 1.3
            else:
                radio = 0.0

            # Страх: чем ближе монстр, тем чаще бьётся сердце и темнее края экрана
            target_fear = 0.0
            if nearest is not None and nearest < FEAR_RANGE:
                target_fear = 1 - nearest / FEAR_RANGE
            fear += (target_fear - fear) * min(1.0, dt * 3)    # плавно, без скачков
            player.tremble = fear > 0.6
            if fear > 0.05:
                heart_timer -= dt
                if heart_timer <= 0:
                    sounds.heartbeat(0.4 + 0.6 * fear)
                    heart_pulse = 1.0
                    heart_timer = 1.1 - 0.65 * fear        # от ~1 удара в секунду до ~2
            else:
                heart_timer = 0.0
        if hurt_flash > 0:                       # красная вспышка: героя ранили
            red = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            red.fill((120, 0, 0, int(110 * hurt_flash)))
            window.blit(red, (0, 0))
            hurt_flash -= dt * 2.5        
        if dead:
            radio = 0.0
            fear = 0.0
            player.tremble = False
        exclaim_timer -= dt
        shake_timer -= dt
        heart_pulse = max(0.0, heart_pulse - dt * 3)
        sounds.radio(radio)
        sounds.music(dt, radio, dead or intro.phase == "text")

        broken_on, switched_on = loc.lamps.update(dt)
        audible_glows = [g for g in glows if loc.lamps.level_at(*g) > .2]
        sounds.update(dt, player.rect.centerx, player.rect.centery, audible_glows, broken_on, switched_on)

        # Камера: куда смотрим — на машину (во вступлении) или на героя.
        # Когда герой выходит, камера плавно переезжает от машины к нему.
        if hero_visible:
            focus_blend = min(1.0, focus_blend + dt / 0.8)
        b = smoothstep(0.0, 1.0, focus_blend)
        focus_x = round(car.centerx * (1 - b) + player.rect.centerx * b)
        focus_y = round(car.centery * (1 - b) + player.rect.centery * b)
        cam_x = focus_x - GAME_W // 2
        cam_y = focus_y - GAME_H // 2
        if shake_timer > 0:                     # камера вздрагивает от испуга
            cam_x += random.randint(-2, 2)
            cam_y += random.randint(-2, 2)
        cam_x = max(0, min(cam_x, map_w - GAME_W))
        cam_y = max(0, min(cam_y, map_h - GAME_H))
        view = pygame.Rect(cam_x - 40, cam_y - 40, GAME_W + 80, GAME_H + 80)

        # --- 3. Рисование мира (маленькое разрешение) ---
        game.fill((8, 8, 10))  # Clear uncovered space when the new map is smaller than the viewport.
        game.blit(map_surf, (-cam_x, -cam_y))
        active_play = playing and not dead and not reading and not inventory_open and not picture and not code_spot
        loc.water.update(dt if active_play else 0, player.rect.center, active_play and player.stepped)
        for _, image, x, y in loc.ground_scenery.props_at(time_total):
            game.blit(image, (x - cam_x, y - cam_y))
        loc.water.draw(game, (cam_x, cam_y))

        if note_rect:   # записка лежит на земле
            draw_note_item(game, note_rect.move(-cam_x, -cam_y))

        if not has_weapon:                      # труба лежит на земле, пока её не подняли
            for r in loc.pipe_rects:
                draw_pipe_item(game, r.move(-cam_x, -cam_y))

        # Что у героя в руках: фонарик — в левой, труба — в правой
        player.left_hand = "flashlight" if has_flashlight else None
        player.right_hand = "pipe" if has_weapon else None
        player.light_on = flash_on
        player.swing = 1 - swing_timer / SWING_TIME if swing_timer > 0 else None        
        # Высокие предметы, монстры и герой — по порядку сверху вниз:
        # кто ниже на экране (ближе к нам), тот рисуется позже и закрывает остальных
        animated_props = loc.scenery.props_at(time_total, flags)
        to_draw = [(bottom, (img, x, y)) for bottom, img, x, y in animated_props
                   if view.colliderect(pygame.Rect(x, y, img.get_width() / ART_SCALE, img.get_height() / ART_SCALE))]
        if hero_visible:
            to_draw.append((player.rect.bottom, player))
        to_draw.extend(draw_ground_corpses(game, monsters, (cam_x, cam_y), view))
        to_draw.sort(key=lambda item: item[0])
        for bottom, thing in to_draw:
            if isinstance(thing, tuple):        # картинка предмета
                img, x, y = thing
                game.blit(img, (x - cam_x, y - cam_y))
            else:                               # герой или монстр — рисуют себя сами
                thing.draw(game, cam_x, cam_y)

        if FOG_CLOUDS and not loc.inside:       # клочья тумана плывут поверх улицы
            draw_fog_clouds(game, fog_clouds, cam_x, cam_y, time_total)

        # Настольные лампы: запоминаем, как выглядит место под ними ДО темноты,
        # чтобы потом "проявить" его тусклым конусом поверх тумана
        desk_reveals = []
        for kind, gx, gy in glows:
            if kind != 'desk' or not view.collidepoint(gx, gy):
                continue
            level = loc.lamps.level_at(kind, gx, gy)
            if level < .02:
                continue
            area = desk_cone.get_rect(topleft=(round((gx - desk_center[0] - cam_x) * ART_SCALE),
                                               round((gy - desk_center[1] - cam_y) * ART_SCALE)))
            clip = area.clip(game.surface.get_rect())
            if clip.w and clip.h:
                desk_reveals.append((game.surface.subsurface(clip).copy(), clip, area, level))

        # Туман: центр "дырки" ставим на героя (во вступлении — на машину)
        px = focus_x - cam_x
        py = focus_y - cam_y
        if intro.headlights_on():
            # Фары машины: используем готовый луч фонарика "вправо", только из передка машины
            fog_img, light, beam = flashlight["right"]
            R = FLASH_RANGE
            hx, hy = FLASH_ORIGIN["right"]
            fx = car.right - 1 - cam_x
            fy = car.centery - cam_y
            game.blit(light, (fx - R, fy - R), special_flags=pygame.BLEND_RGB_ADD)
            game.blit(fog_img, (fx - hx - GAME_W, fy - hy - GAME_H))
            game.blit(beam, (fx - R, fy - R), special_flags=pygame.BLEND_RGB_ADD)
        elif flash_on:
            fog_img, light, beam = flashlight[player.facing]
            R = FLASH_RANGE
            hx, hy = FLASH_ORIGIN[player.facing]
            # Луч не проходит сквозь дома, заборы и машины — обрезаем его там, где он упирается
            fog_img, light, beam = occlude_flashlight(
                loc.light_grid, fog, fog_img, light, beam,
                player.rect.centerx + hx, player.rect.centery + hy, player.facing, hx, hy)
            # Свет на земле — до тумана, потом туман с вырезанным лучом, потом свечение в тумане
            game.blit(light, (px + hx - R, py + hy - R), special_flags=pygame.BLEND_RGB_ADD)
            game.blit(fog_img, (px - GAME_W, py - GAME_H))
            game.blit(beam, (px + hx - R, py + hy - R), special_flags=pygame.BLEND_RGB_ADD)
        else:
            game.blit(fog, (px - GAME_W, py - GAME_H))

        # Тусклый свет настольной лампы: сцена под лампой, умноженная на конус, поверх темноты
        for scene, clip, area, level in desk_reveals:
            lit = desk_cone.subsurface(clip.move(-area.x, -area.y)).copy()
            lit.fill((round(255 * DESK_BRIGHTNESS * level),) * 3, special_flags=pygame.BLEND_RGB_MULT)
            scene.blit(lit, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            game.surface.blit(scene, clip.topleft, special_flags=pygame.BLEND_RGB_MAX)
            glow = lit                                      # и лёгкая тёплая дымка в самом конусе
            glow.fill((40, 40, 40), special_flags=pygame.BLEND_RGB_MULT)
            game.surface.blit(glow, clip.topleft, special_flags=pygame.BLEND_RGB_ADD)

        # Искорки над предметами, которые можно поднять, — видны даже сквозь туман.
        # Новый предмет: добавь сюда точку (x, y) на карте, где он лежит, пока его не подняли.
        sparkles = []
        if not has_weapon:
            for r in loc.pipe_rects:
                sparkles.append((r.x + 12, r.y + 4))                # труба
        if note_rect:
            sparkles.append((note_rect.centerx + 2, note_rect.y))   # записка
        # Над машиной с фонариком искорки нет — игрок должен догадаться обыскать её сам
        for i, (sx, sy) in enumerate(sparkles):
            # i * 0.37 — чтобы искорки вспыхивали не все разом, а по очереди
            draw_glint(game, sx - cam_x, sy - cam_y, time_total + i * 0.37)

        # Свет фонарей и окон пробивается сквозь туман
        for kind, gx, gy in glows:
            if not view.collidepoint(gx, gy):
                continue
            img = glow_images[kind]
            level = loc.lamps.level_at(kind, gx, gy)
            if kind == 'flame':
                level = .82 + .12 * math.sin(time_total * 11 + gx) + .06 * math.sin(time_total * 23 + gy)
            if level < .01:
                continue
            if level < .99:
                img = img.copy()
                img.set_alpha(round(255 * level))
            half = img.get_width() // (2 * ART_SCALE)
            game.blit(img, (gx - half - cam_x, gy - half - cam_y), special_flags=pygame.BLEND_RGB_ADD)

        # "!" над головой героя (с маленьким "подпрыгиванием" в начале)
        if exclaim_timer > 0 and hero_visible:
            bounce = -2 if exclaim_timer > 1.1 or 0.75 < exclaim_timer < 0.85 else 0
            ex = player.rect.centerx - 3 - cam_x
            ey = player.rect.bottom - HERO_H - 12 - cam_y + bounce
            game.blit(exclaim_img, (ex, ey))

        # Тёмные края экрана от страха, сильнее в момент удара сердца
        if fear > 0.05:
            vignette.set_alpha(int(255 * min(1.0, fear * 0.6 + heart_pulse * fear * 0.35)))
            game.blit(vignette, (0, 0))

        if not loc.inside:
            leaves.draw(game, (cam_x, cam_y), dt)
        motion = (1.4 if player.running else 1.0) if active_play and player.moving else 0
        lens.apply(game.surface, (cam_x, cam_y), loc.name, motion, dt)
        tape.apply(game.surface, dt, radio if playing and not dead else 0)

        # --- 4. Увеличиваем картинку на всё окно ---
        window.fill((0, 0, 0, 0))

        # --- 5. Интерфейс (текст рисуем уже в большом разрешении, чтобы был чётким) ---
        # Цвет текста: на светлом тумане — тёмный, в тёмном помещении — светлый
        text_color = (200, 196, 188) if loc.inside else (30, 30, 35)
        if intro.phase == "text":
            intro.draw_text(window, intro_font, small_font)
            present(window, display, game.surface)
            continue                            # пока идёт текст, больше ничего не рисуем
        if intro.black_alpha() > 0:             # сцена плавно проявляется из темноты
            black = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            black.fill((0, 0, 0, intro.black_alpha()))
            window.blit(black, (0, 0))

        # Мысль героя — курсивом, плавно исчезает в последнюю секунду
        thought_timer -= dt
        if thought_timer > 0 and not reading and not dead:
            draw_thought(window, thought_font, thought, int(255 * min(1.0, thought_timer * 2)), text_color)

        # Подсказка по управлению — ниже, обычным шрифтом
        # (если рядом есть записка или машина, место внизу занимает их подсказка)
        hint_timer -= dt
        if hint_timer > 0 and not reading and not dead and not near_note and not near_car and not near_spot and not near_door and not near_pipe:
            draw_hint(window, font, hint, text_color, alpha=int(255 * min(1.0, hint_timer)))

        if near_car and not reading and not dead:
            draw_hint(window, font, "[E] обыскать машину", text_color)

        if has_flashlight:
            draw_text(window, font, "Фонарик: " + ("вкл" if flash_on else "выкл") + "  [F]",
                      (16, 12), color=text_color)

        if has_weapon:
            draw_text(window, font, "Труба  [Пробел]", (16, 40), color=text_color)

        # Полоска здоровья — пока скрыта (включается SHOW_HP = True в settings.py)
        if SHOW_HP and playing:
            bar = pygame.Rect(16, 70, 160, 8)
            pygame.draw.rect(window, (40, 40, 45), bar)
            fill = pygame.Rect(bar.x, bar.y, int(bar.width * max(0, player.hp) / player.max_hp), bar.height)
            pygame.draw.rect(window, (170, 40, 40), fill)
            pygame.draw.rect(window, (25, 25, 30), bar, 1)

        # Полоска выносливости — видна, только когда герой устал
        if playing and player.stamina < 1.0:
            bar = pygame.Rect(16, WIN_H - 24, 160, 8)
            pygame.draw.rect(window, (40, 40, 45), bar)                      # фон полоски
            fill = pygame.Rect(bar.x, bar.y, int(bar.width * player.stamina), bar.height)  # заполненная часть
            color = (150, 60, 50) if player.tired else (200, 196, 188)     # выдохся — красная
            pygame.draw.rect(window, color, fill)
            pygame.draw.rect(window, (25, 25, 30), bar, 1)                 # рамка

        if near_note and not reading:
            draw_hint(window, font, "[E] прочитать записку", text_color)

        if near_pipe and not reading:
            draw_hint(window, font, "[E] поднять трубу", text_color)

        if near_door and not reading:
            if near_door.locked:
                door_hint = near_door.locked_hint
            else:
                door_hint = near_door.hint
            draw_hint(window, font, door_hint, text_color)

        if near_spot and not reading:
            if picture_next and near_spot is picture_spot:
                draw_hint(window, font, PICTURE_HINTS.get(picture_next, "[E] посмотреть рисунок"), text_color)
            elif near_spot.code and not near_spot.solved:
                draw_hint(window, font, CODE_HINT, text_color)
            else:
                draw_hint(window, font, "[E] осмотреть", text_color)

        if reading:
            draw_note(window, note_font, font)

        picture_guard -= dt
        if picture:
            draw_picture(window, font, picture)
        found_timer -= dt
        if found_item and found_timer > 0 and not code_spot and not inventory_open:
            draw_found_item(window, font, item_icons[found_item], ITEMS[found_item]["name"],
                            min(1.0, found_timer, (FOUND_TIME - found_timer) * 4))
        code_error -= dt
        if code_spot:
            draw_code_pad(window, font, big_font, code_digits, len(code_spot.code), code_error)
        if inventory_open:
            draw_inventory(window, font, small_font, inventory, inv_choice, item_icons)
        elif inventory and playing and not reading and not dead:
            label = "Инвентарь  [I]"
            draw_text(window, small_font, label, (WIN_W - 16 - small_font.size(label)[0], 14), color=text_color)

        if door_fade > 0:                        # после двери экран плавно светлеет
            black = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            black.fill((0, 0, 0, int(255 * door_fade)))
            window.blit(black, (0, 0))
            door_fade -= dt * 2

        if dead:
            # Экран постепенно заливается красным
            red = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            red.fill((90, 0, 0, min(210, int(dead_timer * 160))))
            window.blit(red, (0, 0))
            draw_text(window, big_font, "ТЫ ПОГИБ", (WIN_W // 2, WIN_H // 2 - 20),
                      color=(210, 190, 180), alpha=min(255, int(dead_timer * 200)), center=True)
            if dead_timer > 1.5:
                draw_text(window, font, "[R] — начать заново", (WIN_W // 2, WIN_H // 2 + 40),
                          color=(200, 180, 170), center=True)

        present(window, display, game.surface)


if __name__ == "__main__":
    main()

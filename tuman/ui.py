# =====================================================
#  ui.py — всё, что рисуется текстом поверх игры:
#  мысли героя, подсказки, записка.
# =====================================================

import os
import pygame
from settings import *
from world import item_image
from texts import *

def draw_text(surf, font, text, pos, color=(230, 230, 230), alpha=255, center=False):
    img = font.render(text, True, color)
    img.set_alpha(alpha)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surf.blit(img, rect)


def wrap_text(font, text, max_width):
    """Разбивает длинную фразу на строки, чтобы каждая влезала в max_width пикселей."""
    lines = []
    line = ""
    for word in text.split(" "):
        test = word if not line else line + " " + word
        if font.size(test)[0] <= max_width:
            line = test
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def draw_thought(window, font, text, alpha, color=None):
    """Мысль героя — внизу по центру, светлым курсивом на полупрозрачной тёмной плашке.
    alpha — от 0 до 255, чтобы мысль плавно исчезала вместе с плашкой."""
    lines = wrap_text(font, text, 500)                     # длинную мысль — в несколько строк
    line_h = 28
    box = pygame.Rect(0, 0, max(font.size(line)[0] for line in lines) + 40, len(lines) * line_h + 18)
    box.x = (WIN_W - box.w) // 2                           # по центру экрана
    box.y = WIN_H - box.h - 44                             # внизу, над строкой подсказок

    plate = pygame.Surface(box.size, pygame.SRCALPHA)
    pygame.draw.rect(plate, (12, 12, 16, int(alpha * 0.45)), plate.get_rect(), border_radius=8)
    pygame.draw.rect(plate, (210, 206, 198, int(alpha * 0.2)), plate.get_rect(), 1, border_radius=8)  # тонкая рамка
    window.blit(plate, box)

    for i, line in enumerate(lines):
        draw_text(window, font, line, (box.centerx, box.y + 9 + line_h // 2 + i * line_h),
                  color=(228, 222, 210), alpha=alpha, center=True)

def draw_hint(window, font, text, color, alpha=255):
    """Подсказка по управлению — в правом нижнем углу, прижата к правому краю."""
    w, h = font.size(text)
    draw_text(window, font, text, (WIN_W - 16 - w, WIN_H - 14 - h), color=color, alpha=alpha)

def thought_time(text):
    """Сколько секунд показывать фразу: чем длиннее, тем дольше."""
    return 1.5 + len(text) / 20


_note_image = None   # картинка записки (загружается один раз)


def draw_note(window, note_font, font):
    """Записка: картинка листка (data/pictures/note.png), под ней — тот же текст печатными буквами,
    если почерк не разобрать. Внизу — подсказка."""
    global _note_image
    if _note_image is None:
        img = pygame.image.load(os.path.join(DATA_DIR, "pictures", "note.png")).convert_alpha()
        k = min(620 / img.get_width(), 360 / img.get_height())      # чтобы влезла в 620x360
        _note_image = pygame.transform.smoothscale(img, (int(img.get_width() * k), int(img.get_height() * k)))

    shade = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 215))
    window.blit(shade, (0, 0))

    rect = _note_image.get_rect()
    rect.x = (WIN_W - rect.w) // 2
    rect.y = 16
    window.blit(_note_image, rect)

    # Расшифровка: строки записки обычным шрифтом под картинкой (пустые строки пропускаем)
    lines = [line for line in NOTE_TEXT if line]
    for i, line in enumerate(lines):
        draw_text(window, font, line, (WIN_W // 2, rect.bottom + 24 + i * 26),
                  color=(170, 164, 154), center=True)

    draw_text(window, font, "[E] — закрыть", (WIN_W // 2, WIN_H - 22), color=(120, 116, 110), center=True)



# ---------- ИНВЕНТАРЬ ----------
INV_SLOTS = 6            # сколько клеточек показывать (если предметов больше — клеток станет больше)



def load_item_icons():
    """Нативные иконки 32x32, показанные в слотах интерфейса размером 64x64."""
    icons = {}
    for name in ITEMS:
        img = item_image(name + "_icon")
        icons[name] = pygame.transform.scale(img, (64, 64))
    return icons


def draw_inventory(window, font, small_font, inventory, choice, icons):
    """Окно инвентаря: ряд клеточек с предметами, внизу — название и описание выбранного."""
    shade = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 230))
    window.blit(shade, (0, 0))
    draw_text(window, font, "ИНВЕНТАРЬ", (WIN_W // 2, 80), color=(200, 196, 188), center=True)

    slots = max(INV_SLOTS, len(inventory))
    size, gap = 88, 16
    left = (WIN_W - (slots * size + (slots - 1) * gap)) // 2       # чтобы ряд стоял по центру
    for i in range(slots):
        box = pygame.Rect(left + i * (size + gap), 150, size, size)
        pygame.draw.rect(window, (34, 34, 40), box)                 # фон клеточки
        if i < len(inventory):
            icon = icons[inventory[i]]
            window.blit(icon, icon.get_rect(center=box.center))
        border = (220, 200, 160) if i == choice and inventory else (70, 70, 78)
        pygame.draw.rect(window, border, box, 3 if i == choice and inventory else 1)

    if not inventory:
        draw_text(window, small_font, "Пусто", (WIN_W // 2, 300), color=(130, 130, 136), center=True)
    else:
        item = ITEMS[inventory[choice]]
        draw_text(window, font, item["name"], (WIN_W // 2, 290), color=(220, 210, 190), center=True)
        for i, line in enumerate(wrap_text(small_font, item["about"], 560)):
            draw_text(window, small_font, line, (WIN_W // 2, 330 + i * 24), color=(170, 164, 156), center=True)
        if "use" in item:
            draw_text(window, small_font, item["use"], (WIN_W // 2, 410), color=(220, 200, 160), center=True)

    draw_text(window, small_font, "A / D — выбор      [I] — закрыть", (WIN_W // 2, WIN_H - 40),
              color=(110, 110, 116), center=True)



# ---------- КАРТИНКА НА ВЕСЬ ЭКРАН ----------
_pictures = {}   # уже загруженные картинки


def draw_picture(window, font, name):
    """Картинка из data/pictures/<name>.png поверх игры (как записка), снизу — подсказка."""
    if name not in _pictures:
        img = pygame.image.load(os.path.join(DATA_DIR, "pictures", name + ".png")).convert_alpha()
        # Уменьшаем, чтобы влезла в 680x440, сохраняя пропорции
        k = min(680 / img.get_width(), 440 / img.get_height())
        _pictures[name] = pygame.transform.smoothscale(img, (int(img.get_width() * k), int(img.get_height() * k)))
    img = _pictures[name]

    shade = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 215))
    window.blit(shade, (0, 0))
    rect = img.get_rect()
    rect.x = (WIN_W - rect.w) // 2
    rect.y = (WIN_H - 40 - rect.h) // 2
    window.blit(img, rect)
    draw_text(window, font, "[E] — закрыть", (WIN_W // 2, WIN_H - 26), color=(190, 185, 175), center=True)

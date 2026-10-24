# =====================================================
#  ui.py — всё, что рисуется текстом поверх игры:
#  мысли героя, подсказки, записка.
# =====================================================

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


def draw_thought(window, font, text, alpha, color=(35, 35, 40)):
    """Мысль героя внизу экрана; если длинная — в несколько строк (последняя — на месте)."""
    lines = wrap_text(font, text, WIN_W - 160)
    for i, line in enumerate(lines):
        y = WIN_H - 70 - (len(lines) - 1 - i) * 28
        draw_text(window, font, line, (WIN_W // 2, y), color=color, alpha=alpha, center=True)


def thought_time(text):
    """Сколько секунд показывать фразу: чем длиннее, тем дольше."""
    return 2.5 + len(text) / 16


def draw_note(window, note_font, font):
    """Записка: на листке — только её текст, подсказка — под листком."""
    shade_surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    shade_surf.fill((0, 0, 0, 170))
    window.blit(shade_surf, (0, 0))

    line_h = 38
    paper = pygame.Rect(0, 0, 520, len(NOTE_TEXT) * line_h + 70)   # высота листка — под количество строк
    paper.center = (WIN_W // 2, WIN_H // 2 - 20)
    pygame.draw.rect(window, (214, 208, 188), paper)
    pygame.draw.rect(window, (120, 110, 95), paper, 3)

    for i, line in enumerate(NOTE_TEXT):
        draw_text(window, note_font, line, (paper.centerx, paper.y + 50 + i * line_h),
                  color=(48, 40, 34), center=True)

    draw_text(window, font, "[E] — закрыть", (paper.centerx, paper.bottom + 30),
              color=(190, 185, 175), center=True)



# ---------- ИНВЕНТАРЬ ----------
INV_SLOTS = 6            # сколько клеточек показывать (если предметов больше — клеток станет больше)



def load_item_icons():
    """Иконки для инвентаря: data/items/<имя>_icon.png (16x16), увеличенные в 4 раза."""
    icons = {}
    for name in ITEMS:
        img = item_image(name + "_icon")
        icons[name] = pygame.transform.scale(img, (img.get_width() * 4, img.get_height() * 4))
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
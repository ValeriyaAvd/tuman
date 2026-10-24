# =====================================================
#  tools/generate_sounds.py — создаёт стандартные звуки игры в папке data/sounds.
#
#  Игре этот скрипт НЕ нужен: она просто загружает готовые файлы.
#  Запускай его, только если хочешь вернуть стандартные звуки
#  (например, после того как заменил их своими и передумал):
#
#      python tools/generate_sounds.py
#
#  Внимание: он перезапишет файлы с такими же именами в data/sounds.
# =====================================================

import os
import math
import wave
import array
import random

RATE = 22050                                   # частота: сколько чисел в одной секунде звука
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sounds")

# ---------- ЗВУК ----------
# Все звуки не загружаются из файлов, а "синтезируются" прямо в коде:
# звук — это просто длинный список чисел от -1 до 1 (положение мембраны динамика).
# Синусоида даёт чистый тон, случайные числа — шум (ветер, шорох, шаги).
# "Огибающая" (envelope) — это громкость звука во времени: резко вверх и плавно вниз.
#

def lowpass(samples, k):
    """Фильтр: убирает высокие частоты. Чем меньше k, тем глуше звук."""
    out = []
    y = 0.0
    for s in samples:
        y += k * (s - y)
        out.append(y)
    return out


def normalize(samples, peak):
    """Делает так, чтобы самый громкий момент звука был равен peak."""
    m = max(abs(s) for s in samples) or 1.0
    return [s * peak / m for s in samples]


def loop_crossfade(samples, fade):
    """Для звуков, которые играют по кругу: плавно склеиваем конец с началом,
    чтобы на стыке не было щелчка. Список должен быть длиннее на fade."""
    body = samples[:-fade]
    tail = samples[-fade:]
    for i in range(fade):
        k = i / fade
        body[i] = body[i] * k + tail[i] * (1 - k)
    return body


def gen_step_hard(rnd, rate):
    """Шаг по асфальту: глухой низкий удар подошвы и немного шороха."""
    out = []
    y1 = y2 = 0.0
    thump_f = rnd.uniform(55, 75)
    for i in range(int(0.12 * rate)):
        t = i / rate
        y1 += 0.12 * (rnd.uniform(-1, 1) - y1)     # двойной фильтр — шум глухой, без "щёлканья"
        y2 += 0.3 * (y1 - y2)
        attack = min(1.0, t / 0.004)               # чуть смягчаем самое начало
        thump = math.sin(2 * math.pi * thump_f * t) * math.exp(-t * 35)
        out.append((y2 * 1.5 + thump) * attack * math.exp(-t * 30))
    return normalize(out, 0.7)


def gen_step_soft(rnd, rate):
    """Шаг по траве: тихий мягкий шорох."""
    out = []
    y1 = y2 = 0.0
    for i in range(int(0.16 * rate)):
        t = i / rate
        y1 += 0.06 * (rnd.uniform(-1, 1) - y1)
        y2 += 0.3 * (y1 - y2)
        crackle = rnd.uniform(-1, 1) * 0.15 if rnd.random() < 0.01 else 0.0   # травинки
        attack = min(1.0, t / 0.02)
        out.append((y2 * 4 + crackle) * attack * math.exp(-t * 20))
    return normalize(out, 0.5)


def gen_step_water(rnd, rate):
    """Шаг по луже: негромкий всплеск и "бульк"."""
    out = []
    y = 0.0
    for i in range(int(0.3 * rate)):
        t = i / rate
        y += 0.3 * (rnd.uniform(-1, 1) - y)
        bubble = math.sin(2 * math.pi * (180 + 500 * t) * t) * math.exp(-t * 18) * 0.4
        out.append((y * math.exp(-t * 16) + bubble))
    return normalize(lowpass(out, 0.3), 0.5)


def gen_wind(rnd, rate):
    """Тихий фоновый ветер с редкими порывами. Играет по кругу всю игру."""
    length = 14.0                        # длина петли: чем длиннее, тем меньше заметен повтор
    fade = int(1.0 * rate)

    # Три порыва в случайные моменты, но каждый в своей трети петли,
    # чтобы они не слиплись в один: (когда, сколько длится, насколько сильный)
    gusts = [((k + rnd.uniform(0.2, 0.8)) * length / 3, rnd.uniform(1.0, 2.2), rnd.uniform(0.25, 0.6))
             for k in range(3)]

    out = []
    y1 = y2 = 0.0
    for i in range(int(length * rate) + fade):
        t = i / rate
        # Двойной фильтр делает шум мягким и глухим — "шуршание", а не "шипение"
        y1 += 0.01 * (rnd.uniform(-1, 1) - y1)
        y2 += 0.05 * (y1 - y2)
        level = 0.3                                          # обычный тихий ветер
        for center, width, strength in gusts:
            d = abs(t % length - center)
            d = min(d, length - d)                           # чтобы порыв не обрывался на стыке петли
            level += strength * math.exp(-(d / width) ** 2)
        # Еле слышный низкий гул где-то на фоне
        drone = 0.004 * math.sin(2 * math.pi * 55.0 * t)
        out.append(y2 * level + drone)
    return normalize(loop_crossfade(out, fade), 0.8)


def gen_buzz(rnd, rate):
    """Жужжание лампы фонаря (электрический гул 100 Гц)."""
    out = []
    for i in range(rate):                # ровно 1 секунда — петля без щелчка
        t = i / rate
        s = (0.5 * math.sin(2 * math.pi * 100 * t)
             + 0.2 * (1 if math.sin(2 * math.pi * 200 * t) > 0 else -1) * 0.4
             + 0.1 * math.sin(2 * math.pi * 300 * t)
             + rnd.uniform(-0.03, 0.03))
        out.append(s)
    return normalize(out, 0.5)


def gen_switch(rnd, rate):
    """Щелчок кнопки фонарика."""
    out = []
    for i in range(int(0.04 * rate)):
        t = i / rate
        click = rnd.uniform(-1, 1) * math.exp(-t * 400)
        tick = math.sin(2 * math.pi * 2200 * t) * math.exp(-t * 250) * 0.5
        out.append(click + tick)
    return normalize(lowpass(out, 0.6), 0.5)


def gen_click(rnd, rate):
    """Треск лампы, когда она загорается."""
    out = []
    for i in range(int(0.05 * rate)):
        t = i / rate
        s = rnd.uniform(-1, 1) * math.exp(-t * 120) + 0.5 * math.sin(2 * math.pi * 1200 * t) * math.exp(-t * 90)
        out.append(s)
    return normalize(out, 0.7)


def gen_paper(rnd, rate):
    """Короткий тихий шорох: герой просто взял бумажку в руки."""
    length = 0.18
    chunk = int(0.008 * rate)                     # каждые 8 мс громкость чуть меняется — "бумажная" фактура
    out = []
    y1 = y2 = 0.0
    amp = 1.0
    for i in range(int(length * rate)):
        t = i / rate
        if i % chunk == 0:
            amp = rnd.uniform(0.6, 1.0)
        y1 += 0.3 * (rnd.uniform(-1, 1) - y1)     # двойной фильтр — мягко, без шипения
        y2 += 0.45 * (y1 - y2)
        env = min(1.0, t / 0.01) * math.exp(-t * 18)   # быстро появляется и быстро гаснет
        out.append(y2 * amp * env)
    return normalize(out, 0.4)


def gen_clang(rnd, rate):
    """Далёкий удар по металлу с эхом."""
    partials = [(170, 0.5, 3), (433, 0.3, 4), (689, 0.25, 6), (1117, 0.15, 8)]
    n = int(3.0 * rate)
    out = [0.0] * n
    for i in range(n):
        t = i / rate
        out[i] = sum(a * math.sin(2 * math.pi * f * t) * math.exp(-t * d) for f, a, d in partials)
    delay = int(0.4 * rate)              # эхо
    for i in range(n - 1, delay - 1, -1):
        out[i] += out[i - delay] * 0.4
    return normalize(lowpass(out, 0.3), 0.7)


def gen_bell(rnd, rate):
    """Далёкий колокол: три медленных звонких удара."""
    base = 330.0
    # Колокол звучит не одной нотой, а несколькими сразу — поэтому он и колокол.
    # (во сколько раз выше основной ноты, громкость, скорость затухания)
    # Высокие призвуки затухают быстрее — сначала "дзинь", потом долгое "оммм".
    partials = [
        (0.5, 0.45, 0.5),     # гул — самый низкий и долгий
        (0.501, 0.3, 0.5),    # почти такой же — вместе с предыдущим даёт "дрожание" звона
        (1.0, 0.5, 0.8),      # основная нота
        (1.003, 0.3, 0.8),    # тоже для дрожания
        (1.2, 0.4, 1.2),      # характерный "колокольный" призвук
        (1.5, 0.25, 1.6),
        (2.0, 0.35, 1.8),
        (2.52, 0.25, 2.6),
        (3.0, 0.2, 3.2),
        (4.07, 0.15, 4.5),    # звонкие верхние призвуки
        (5.4, 0.1, 6.0),
    ]
    toll_len = int(4.5 * rate)
    toll = []
    for i in range(toll_len):
        t = i / rate
        s = sum(a * math.sin(2 * math.pi * base * k * t) * math.exp(-t * d) for k, a, d in partials)
        strike = rnd.uniform(-1, 1) * math.exp(-t * 300) * 0.5      # металлический "тук" языка о колокол
        toll.append(s + strike)
    gap = int(2.4 * rate)                      # пауза между ударами
    out = [0.0] * (gap * 2 + toll_len)
    for n, loud in enumerate((1.0, 0.85, 0.7)):
        for i, s in enumerate(toll):
            out[n * gap + i] += s * loud
    return normalize(lowpass(out, 0.7), 0.6)   # слабый фильтр — чуть приглушаем расстоянием


def gen_far_steps(rnd, rate):
    """Тяжёлые шаги где-то в тумане: низкие глухие удары, чуть громче... и обрываются."""
    out = [0.0] * int(4.5 * rate)
    pos = 0.0
    loud = 0.5
    for _ in range(5):
        start = int(pos * rate)
        y = 0.0
        thump_f = rnd.uniform(28, 36)          # очень низкий удар — больше чувствуется, чем слышится
        for i in range(int(0.45 * rate)):
            t = i / rate
            y += 0.02 * (rnd.uniform(-1, 1) - y)
            attack = min(1.0, t / 0.02)        # мягкое начало, без щелчка
            s = (math.sin(2 * math.pi * thump_f * t) + y * 3) * attack * math.exp(-t * 9)
            if start + i < len(out):
                out[start + i] += s * loud
        pos += rnd.uniform(0.7, 0.9)           # шаги чуть неровные — так идёт кто-то живой
        loud += 0.12                           # приближается...
    delay = int(0.25 * rate)                   # эхо между домами
    for i in range(len(out) - 1, delay - 1, -1):
        out[i] += out[i - delay] * 0.3
    return normalize(lowpass(lowpass(out, 0.06), 0.1), 0.5)


def gen_static(rnd, rate):
    """Шипение радио: шум с "прыгающей" громкостью и щелчками. Играет по кругу."""
    length = 2.0
    fade = int(0.2 * rate)
    chunk = int(0.015 * rate)
    out = []
    fast = slow = 0.0
    amp = 1.0
    for i in range(int(length * rate) + fade):
        n = rnd.uniform(-1, 1)
        fast += 0.8 * (n - fast)
        slow += 0.05 * (n - slow)
        if i % chunk == 0:
            amp = rnd.choice((0.3, 0.6, 1.0, 1.0))
        pop = rnd.uniform(-1, 1) * 2 if rnd.random() < 0.0005 else 0.0   # треск
        out.append((fast - slow) * amp + pop)       # fast - slow = убрали и низы, и самые верха
    return normalize(loop_crossfade(out, fade), 0.7)


def gen_growl(rnd, rate):
    """Хриплый низкий рык монстра, когда он замечает героя."""
    length = 1.4
    out = []
    phase = 0.0
    for i in range(int(length * rate)):
        t = i / rate
        f = 48 + 18 * math.sin(2 * math.pi * 2.5 * t) + rnd.uniform(-6, 6)
        phase += f / rate
        saw = (phase % 1.0) * 2 - 1
        rough = 0.6 + 0.4 * rnd.uniform(-1, 1)      # "хрип" — громкость неровная
        env = math.sin(math.pi * t / length) ** 0.7
        out.append(saw * rough * env)
    return normalize(lowpass(lowpass(out, 0.15), 0.3), 0.8)


def gen_shock(rnd, rate):
    """Короткий удар испуга, когда герой впервые видит монстра (тише, чем звук смерти)."""
    out = []
    for i in range(int(1.0 * rate)):
        t = i / rate
        boom = math.sin(2 * math.pi * 45 * t) * math.exp(-t * 5)
        stab = (math.sin(2 * math.pi * 600 * t) + math.sin(2 * math.pi * 637 * t)) * math.exp(-t * 7) * 0.3
        hit = rnd.uniform(-1, 1) * math.exp(-t * 40) * 0.5
        out.append(boom + stab + hit)
    return normalize(lowpass(out, 0.5), 0.8)


def gen_heartbeat(rnd, rate):
    """Один удар сердца: "тук-тук" (два глухих толчка)."""
    out = []
    for i in range(int(0.5 * rate)):
        t = i / rate
        lub = math.sin(2 * math.pi * 48 * t) * math.exp(-t * 25)
        dub = 0.0
        if t > 0.17:
            td = t - 0.17
            dub = 0.7 * math.sin(2 * math.pi * 58 * td) * math.exp(-td * 30)
        out.append(lub + dub)
    return normalize(lowpass(out, 0.3), 0.9)


def gen_sting(rnd, rate):
    """Резкий пугающий звук, когда монстр догоняет героя."""
    length = 2.2
    out = []
    for i in range(int(length * rate)):
        t = i / rate
        # Несколько близких высоких нот одновременно — звучит "неправильно" и страшно
        strings = sum(math.sin(2 * math.pi * f * t) for f in (740, 784, 1046, 1109))
        strings *= math.exp(-t * 1.2) * min(1.0, t / 0.02)
        boom = math.sin(2 * math.pi * 38 * t) * math.exp(-t * 3) * 1.5
        hit = rnd.uniform(-1, 1) * math.exp(-t * 20)
        out.append(0.25 * strings + boom + 0.6 * hit)
    return normalize(out, 0.9)


# ---------- ЗВУКИ МАШИНЫ (для вступления) ----------
def gen_engine(rnd, rate):
    """Мотор на холостых: низкое ровное "бу-бу-бу". Играет по кругу."""
    f = 28.0                                   # 28 "вспышек" в секунду — обычный холостой ход
    fade = int(0.1 * rate)
    out = []
    y = 0.0
    for i in range(rate + fade):
        t = i / rate
        phase = (f * t) % 1.0
        pulse = math.exp(-phase * 6)           # каждая вспышка в цилиндре — короткий толчок
        hum = (0.5 * math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * 2 * f * t)
               + 0.15 * math.sin(2 * math.pi * 3 * f * t))
        y += 0.05 * (rnd.uniform(-1, 1) - y)   # глухой гул железа
        out.append(pulse * 0.6 + hum + y * 3)
    return normalize(loop_crossfade(lowpass(lowpass(out, 0.08), 0.2), fade), 0.7)


def gen_sputter(rnd, rate):
    """Мотор "кашляет": несколько неровных хлопков."""
    out = [0.0] * int(0.4 * rate)
    for start_s in (0.0, rnd.uniform(0.07, 0.11), rnd.uniform(0.18, 0.25)):
        start = int(start_s * rate)
        y = 0.0
        for i in range(int(0.12 * rate)):
            t = i / rate
            y += 0.2 * (rnd.uniform(-1, 1) - y)
            thump = math.sin(2 * math.pi * 40 * t)
            if start + i < len(out):
                out[start + i] += (y * 2 + thump) * math.exp(-t * 45)
    return normalize(lowpass(out, 0.3), 0.7)


def gen_stall(rnd, rate):
    """Мотор глохнет: толчки всё реже и тише... и последний глухой стук."""
    out = []
    phase = 0.0
    y = 0.0
    for i in range(int(1.6 * rate)):
        t = i / rate
        f = max(3.0, 28 * (1 - t / 1.2))       # частота толчков падает
        phase += f / rate
        pulse = math.exp(-(phase % 1.0) * 6) * math.exp(-t * 1.5)
        y += 0.05 * (rnd.uniform(-1, 1) - y)
        clunk = 0.0
        if t > 1.2:                            # двигатель встал — глухой стук
            tc = t - 1.2
            clunk = math.sin(2 * math.pi * 50 * tc) * math.exp(-tc * 15) * 1.2
        out.append(pulse + y * 2 * math.exp(-t * 2) + clunk)
    return normalize(lowpass(lowpass(out, 0.1), 0.2), 0.7)


def gen_door_open(rnd, rate):
    """Щелчок замка и короткий скрип двери."""
    out = []
    phase = 0.0
    for i in range(int(0.5 * rate)):
        t = i / rate
        latch = rnd.uniform(-1, 1) * math.exp(-t * 300)
        creak = 0.0
        if t > 0.08:
            tc = t - 0.08
            phase += (90 - 50 * tc + rnd.uniform(-10, 10)) / rate
            creak = ((phase % 1.0) * 2 - 1) * math.sin(math.pi * min(1.0, tc / 0.4)) * 0.3
        out.append(latch + creak)
    return normalize(lowpass(out, 0.3), 0.6)


def gen_door_slam(rnd, rate):
    """Дверь захлопывается: тяжёлый глухой удар и дребезг."""
    out = []
    y = 0.0
    for i in range(int(0.6 * rate)):
        t = i / rate
        thump = math.sin(2 * math.pi * 45 * t) * math.exp(-t * 12)
        y += 0.3 * (rnd.uniform(-1, 1) - y)
        rattle = y * math.exp(-t * 30)
        out.append(thump + rattle)
    return normalize(lowpass(out, 0.3), 0.8)


# ---------- ФОНОВАЯ МЕЛОДИЯ ----------
# Тихий фон в ля миноре: только мягкие аккорды-"подушки", которые медленно сменяют
# друг друга. Каждый аккорд длится MUSIC_BAR секунд.
# Ноты Bb (си-бемоль) и F поверх E звучат чуть "неправильно" — это и создаёт напряжение.
MUSIC_BAR = 4.0
MUSIC_CHORDS = [               # по одному аккорду на такт
    ["A2", "E3", "B3", "C4"],  # ля минор с "лишней" нотой си — грустно и тревожно
    ["F2", "C3", "E3", "A3"],
    ["D2", "A2", "E3", "F3"],
    ["E2", "B2", "D3", "F3"],  # F поверх E — диссонанс, ощущение "что-то не так"
    ["A2", "E3", "A3", "C4"],
    ["Bb2", "F3", "A3", "D4"], # си-бемоль — "чужой" аккорд, самое тревожное место
    ["D2", "A2", "F3", "A3"],
    ["E2", "B2", "E3", "G#3"], # тянет обратно к началу — петля замыкается
]
def note_freq(name):
    """Название ноты -> частота в герцах. 'A4' — это ля первой октавы, 440 Гц.
    Можно с диезом (#) или бемолем (b): 'G#4', 'Bb3'."""
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    n = names[name[0]]
    rest = name[1:]
    if rest[0] == "#":
        n += 1
        rest = rest[1:]
    elif rest[0] == "b":
        n -= 1
        rest = rest[1:]
    midi = (int(rest) + 1) * 12 + n          # номер клавиши, как на синтезаторе
    return 440.0 * 2 ** ((midi - 69) / 12)   # каждая следующая клавиша выше в 2^(1/12) раз


def gen_music(rnd, rate):
    """Создаёт всю мелодию. Чтобы было быстрее, считаем с вдвое меньшей частотой
    (для таких мягких звуков разницы не слышно), а в конце "растягиваем" обратно."""
    r = rate // 2
    two_pi = 2 * math.pi
    length = len(MUSIC_CHORDS) * MUSIC_BAR
    tail = 6.0                                     # "хвост": эхо после последнего такта
    n = int((length + tail) * r)
    out = [0.0] * n

    # 1) Аккорды-подушки: каждая нота — две чуть расстроенные синусоиды,
    #    из-за этого звук "плавает", как у синтезатора
    attack, release = 1.5, 1.5
    for bar, chord in enumerate(MUSIC_CHORDS):
        start = int(bar * MUSIC_BAR * r)
        waves = [(two_pi * note_freq(x) * 0.9985 / r, two_pi * note_freq(x) * 1.0015 / r) for x in chord]
        for i in range(int((MUSIC_BAR + release) * r)):
            t = i / r
            env = min(1.0, t / attack)             # медленно появляется...
            if t > MUSIC_BAR:
                env *= max(0.0, 1 - (t - MUSIC_BAR) / release)   # ...и медленно уходит
            env *= 0.85 + 0.15 * math.sin(two_pi * 0.25 * t)     # еле заметно "дышит"
            s = 0.0
            for w1, w2 in waves:
                s += math.sin(w1 * i) + math.sin(w2 * i)
            out[start + i] += s * env * 0.05

    # 2) Эхо — звук как будто в большом пустом пространстве
    for delay_s, feedback in ((0.43, 0.38), (0.29, 0.3)):
        d = int(delay_s * r)
        for i in range(d, n):
            out[i] += out[i - d] * feedback
    out = lowpass(out, 0.5)

    # 3) Петля без шва: "хвост" после конца накладываем на начало
    loop_len = int(length * r)
    for i in range(n - loop_len):
        out[i] += out[loop_len + i]
    out = normalize(out[:loop_len], 0.6)

    # 4) Растягиваем обратно до полной частоты: между соседними точками вставляем среднее
    full = []
    for i in range(loop_len):
        a = out[i]
        b = out[(i + 1) % loop_len]
        full.append(a)
        full.append((a + b) / 2)
    return full


def save_wav(name, samples):
    """Сохраняет список чисел от -1 до 1 как обычный .wav (моно, 16 бит)."""
    path = os.path.join(OUT_DIR, name + ".wav")
    data = array.array("h", (int(max(-1.0, min(1.0, s)) * 32000) for s in samples))
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(data.tobytes())
    print("  ", name + ".wav")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Создаю звуки в", os.path.abspath(OUT_DIR))
    rnd = random.Random(1)     # одно и то же "зерно" — звуки всегда получаются одинаковыми
    for i in range(4):
        save_wav(f"step_hard_{i + 1}", gen_step_hard(rnd, RATE))
    for i in range(4):
        save_wav(f"step_soft_{i + 1}", gen_step_soft(rnd, RATE))
    for i in range(2):
        save_wav(f"step_water_{i + 1}", gen_step_water(rnd, RATE))
    save_wav("lamp_click", gen_click(rnd, RATE))
    save_wav("flashlight_click", gen_switch(rnd, RATE))
    save_wav("note_paper", gen_paper(rnd, RATE))
    save_wav("far_clang", gen_clang(rnd, RATE))
    save_wav("far_bell", gen_bell(rnd, RATE))
    save_wav("far_steps", gen_far_steps(rnd, RATE))
    save_wav("monster_growl", gen_growl(rnd, RATE))
    save_wav("death", gen_sting(rnd, RATE))
    save_wav("monster_shock", gen_shock(rnd, RATE))
    save_wav("heartbeat", gen_heartbeat(rnd, RATE))
    save_wav("wind", gen_wind(rnd, RATE))
    save_wav("lamp_buzz", gen_buzz(rnd, RATE))
    save_wav("radio_static", gen_static(rnd, RATE))
    save_wav("car_engine", gen_engine(rnd, RATE))
    save_wav("car_sputter", gen_sputter(rnd, RATE))
    save_wav("car_stall", gen_stall(rnd, RATE))
    save_wav("car_door_open", gen_door_open(rnd, RATE))
    save_wav("car_door_slam", gen_door_slam(rnd, RATE))
    print("Создаю мелодию (несколько секунд)...")
    save_wav("music", gen_music(rnd, RATE))
    print("Готово!")


if __name__ == "__main__":
    main()

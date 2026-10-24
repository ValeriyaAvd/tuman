# Туман

2D хоррор на pygame-ce. Исходники игры находятся в папке `tuman/`.
Графика использует тайлы 32×32 и нативный холст 640×360; описание обновления — [ART.md](tuman/ART.md).

## Запуск

Python 3.10+:

```powershell
python -m pip install -r requirements.txt
cd tuman
python main.py
```

WASD / стрелки — ходьба, Shift — бег, E — взаимодействие, F — фонарик,
Пробел — удар / пропуск вступления, I / Tab — инвентарь, F11 — полный экран.

## Редактирование в Tiled

1. Открой в Tiled проект `tuman/data/maps/Tuman.tiled-project`.
2. Открой `street.tmj` или `shop.tmj` в дереве проекта.
3. Рисуй покрытия на тайловом слое, расставляй предметы на объектном слое.
4. Сохрани карту и перезапусти игру. Экспорт или повторная генерация ресурсов не нужны.

Подробная инструкция по слоям, дверям и созданию новых локаций: [TILED.md](tuman/TILED.md).

Проверить карты и тесты (из папки `tuman/`):

```powershell
python tools/check_maps.py
python -m unittest discover -s tests -v
```

Windows-сборка (PowerShell, из корня репозитория):

```powershell
# Один раз установить зависимости в используемый Python:
python -m pip install -r requirements-build.txt
# Каждая следующая сборка:
powershell -ExecutionPolicy Bypass -File .\build.ps1
# Пересобрать и запустить:
powershell -ExecutionPolicy Bypass -File .\build.ps1 -Run
```

Скрипт использует `.venv/Scripts/python.exe`, если окружение существует, иначе Python из PATH.
Можно явно указать `-Python C:\путь\python.exe`. Результат: `tuman/dist/Tuman/Tuman.exe`.
Перед пересборкой закрой запущенный `.exe`. Обычная сборка сохраняет кеш PyInstaller;
добавь `-Clean`, только если нужна полная пересборка. Передавай игрокам всю папку `dist/Tuman/`.

Для обычной разработки пересборка не нужна: запускай `python main.py` из папки `tuman/`.
Весь каталог `data/`, включая новые карты и тайлсеты, включается в сборку.
После изменения исходников или ресурсов сборку нужно обновлять. Скрипт обновляет `dist/Tuman/`,
но не создаёт заново `dist.zip`.

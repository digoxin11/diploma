#!/usr/bin/env python3
"""
download_2gis_traffic.py

Массовая загрузка тайлов пробок 2GIS по прямоугольнику (Алматы).
Работает на Windows и Unix. Требует Python 3.7+ и библиотеку requests.

Скрипт сначала пытается обратиться к локальному On-Premise Traffic Proxy (Docker).
Если прокси недоступен, автоматически переходит на публичный Tiles API с "map,traffic" слоем и API-ключом.

Как использовать:
 1. Установите Python 3.7+ и создайте виртуальное окружение:
      python -m venv venv
      # Windows:
      .\venv\Scripts\activate
      # Unix/macOS:
      source venv/bin/activate
 2. Установите зависимости:
      pip install requests
 3. Получите или подготовьте API_KEY с https://dev.2gis.com/map/ (раздел Traffic).
 4. Откройте и отредактируйте поля ниже (API_KEY, BBOX, ZOOM, INTERVAL_SEC, DURATION_SEC).
 5. Запустите:
      python download_2gis_traffic.py

Скрипт сохраняет PNG-тайлы в папке tiles_2gis/<метка_времени>/tile_<x>_<y>.png
"""
import os
import math
import time
import requests
from datetime import datetime, timedelta
from requests.exceptions import RequestException

# ====== КОНФИГУРАЦИЯ ======
# Задайте свой API-ключ 2GIS для публичного Tiles API
API_KEY       = "08101265-79e2-4f69-90e9-1ed6e35d6227"
# Локальный прокси (On-Premise Traffic Proxy)
PROXY_URL     = "http://localhost:8080/traffic/tiles"
# Координаты Алматы
LAT_MIN, LAT_MAX = 43.0, 44.0
LON_MIN, LON_MAX = 76.0, 78.0
# Масштаб
ZOOM            = 13
# Интервалы
INTERVAL_SEC    = 60    # период между снимками (с)
DURATION_SEC    = 3600  # общее время (с)
# Выходная папка
OUTPUT_DIR      = "tiles_2gis"
# URL публичного Tiles API
PUBLIC_URL      = "https://tile2.maps.2gis.com/tiles"
TIMEOUT         = 10
# ===========================

def deg2num(lat: float, lon: float, zoom: int) -> (int, int):
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1/math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_range(lat_min: float, lat_max: float, lon_min: float, lon_max: float, zoom: int):
    x0, y1 = deg2num(lat_min, lon_min, zoom)
    x1, y0 = deg2num(lat_max, lon_max, zoom)
    return range(min(x0, x1), max(x0, x1) + 1), range(min(y0, y1), max(y0, y1) + 1)


def fetch_tile(x: int, y: int, ts: datetime) -> bytes:
    """
    Пытается скачать тайл сначала с локального прокси, затем с публичного API.
    """
    params = {'x': x, 'y': y, 'z': ZOOM}
    # пробуем локальный прокси
    try:
        r = requests.get(PROXY_URL, params=params, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.content
    except RequestException:
        pass
    # fallback на публичный Tiles API
    params.update({'layers': 'map,traffic', 'key': API_KEY})
    r2 = requests.get(PUBLIC_URL, params=params, timeout=TIMEOUT)
    if r2.status_code == 200:
        return r2.content
    else:
        raise RequestException(f"Status {r2.status_code}")


def download_tiles_for_timestamp(ts: datetime):
    stamp = ts.strftime("%Y%m%d_%H%M%S")
    out_folder = os.path.join(OUTPUT_DIR, stamp)
    os.makedirs(out_folder, exist_ok=True)

    xs, ys = tile_range(LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, ZOOM)
    print(f"[{stamp}] Z={ZOOM}, X={min(xs)}–{max(xs)}, Y={min(ys)}–{max(ys)}")

    for x in xs:
        for y in ys:
            try:
                data = fetch_tile(x, y, ts)
                path = os.path.join(out_folder, f"tile_{x}_{y}.png")
                with open(path, 'wb') as f:
                    f.write(data)
            except RequestException as e:
                print(f"  [SKIP] tile {x},{y}: {e}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start = datetime.utcnow()
    end = start + timedelta(seconds=DURATION_SEC)
    ts = start
    while ts <= end:
        download_tiles_for_timestamp(ts)
        ts += timedelta(seconds=INTERVAL_SEC)
        time.sleep(INTERVAL_SEC)

if __name__ == '__main__':
    main()

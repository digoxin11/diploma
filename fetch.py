#!/usr/bin/env python3
import os
import time
import json
import requests
from datetime import datetime

# === НАСТРОЙКИ ===
API_KEY = "08101265-79e2-4f69-90e9-1ed6e35d6227"
PROXY_URL = "https://traffic-jams.2gis.com"  # Если используешь свой прокси, замени на http://your-proxy/2gis/traffic-jams
BBOX = (76.70, 43.14, 77.20, 43.35)  # Вся Алматы
ZOOM = 12
SAVE_DIR = "data"
INTERVAL_SECONDS = 120  # Раз в 2 минуты
MAX_DAYS = 31  # Один месяц

# === ФУНКЦИИ ===

def fetch_traffic():
    headers = {
        "X-API-Key": API_KEY
    }
    params = {
        "bbox": ",".join(map(str, BBOX)),
        "zoom": ZOOM,
        "ts": int(time.time() * 1000),  # Уникальный timestamp, чтобы избежать кэша
    }
    response = requests.get(PROXY_URL, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def save_json(data, count):
    os.makedirs(SAVE_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = os.path.join(SAVE_DIR, f"traffic_{ts}_{count}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[{count}] Сохранено: {filename}")

# === ОСНОВНОЙ ЦИКЛ ===

total_iterations = (MAX_DAYS * 24 * 60) // (INTERVAL_SECONDS // 60)
print(f"🚦 Запуск сбора данных о пробках на {MAX_DAYS} дней (~{total_iterations} файлов)...\n")

counter = 1
while counter <= total_iterations:
    try:
        traffic_data = fetch_traffic()
        save_json(traffic_data, counter)
    except Exception as e:
        print(f"❌ Ошибка на шаге {counter}: {e}")
    time.sleep(INTERVAL_SECONDS)
    counter += 1

print("✅ Сбор данных завершён.")

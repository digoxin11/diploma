import requests
import os
import csv
from datetime import datetime

# Мой ключ
API_KEY = "a1b2c3d4-5e6f-7890-abcd-1234567890ef"

# Создаём папку
SAVE_DIR = "traffic_data"
os.makedirs(SAVE_DIR, exist_ok=True)

# 80 координат (распределены по Алматы)
POINTS = [
    (43.24 + i * 0.001, 76.85 + (i % 8) * 0.005) for i in range(80)
]

# Запрос данных на 24 часа
for hour in range(24):
    timestamp = f"2025-05-02T{hour:02d}:00:00Z"
    filename = os.path.join(SAVE_DIR, f"traffic_{hour:02d}.csv")

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["lat", "lon", "currentSpeed", "freeFlowSpeed", "timestamp"])

        for lat, lon in POINTS:
            url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
            params = {
                "point": f"{lat},{lon}",
                "unit": "KMPH",
                "key": API_KEY
            }

            try:
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()["flowSegmentData"]
                    writer.writerow([
                        lat,
                        lon,
                        data["currentSpeed"],
                        data["freeFlowSpeed"],
                        timestamp
                    ])
                else:
                    print(f"❌ Ошибка: {response.status_code} на {lat}, {lon}")
            except Exception as e:
                print("⚠️ Ошибка запроса:", e)

    print(f"✅ Сохранено: traffic_{hour:02d}.csv")

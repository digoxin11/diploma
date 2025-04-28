import os
import time
import json
import csv
import sqlite3
import requests
from datetime import datetime, timedelta, timezone

# === НАСТРОЙКИ ===
API_KEY = "VQcLatOpIuCn5ACclAucCeXMuQJwwJV0"
SAVE_DIR = "diploma"
CSV_FILE = os.path.join(SAVE_DIR, "traffic_data.csv")
DB_FILE = os.path.join(SAVE_DIR, "traffic.db")
INTERVAL_SECONDS = 45
RETENTION_DAYS = 7
LOCATIONS = [
    (43.2396, 76.7982), (43.239578, 76.815811), (43.239556, 76.833422),
    (43.239533, 76.851033), (43.239511, 76.868644), (43.239489, 76.886256),
    (43.239467, 76.903867), (43.239444, 76.921478), (43.239422, 76.939089),
    (43.2394, 76.9567),  # Абая — 10

    (43.3141, 76.8673), (43.2963, 76.8673), (43.2785, 76.8673), (43.2607, 76.8673),
    (43.2429, 76.8673), (43.2251, 76.8673), (43.2073, 76.8673), (43.1895, 76.8673),
    (43.1794, 76.8673),  # Саина — 9

    (43.2065, 76.8415), (43.2127, 76.863625), (43.2189, 76.88575), (43.2251, 76.907875),
    (43.2313, 76.93), (43.2375, 76.952125), (43.2435, 76.974),  # Аль-Фараби — 7

    (43.2554, 76.7987), (43.2554, 76.817025), (43.2554, 76.83535), (43.2554, 76.853675),
    (43.2553, 76.872), (43.2553, 76.890325), (43.2553, 76.90865), (43.2553, 76.926975),
    (43.2553, 76.9453), (43.2553, 76.9575),  # Толе би — 10

    (43.3312, 76.8428), (43.3083, 76.8428), (43.2854, 76.8428), (43.2625, 76.8428),
    (43.2396, 76.8428), (43.2167, 76.8428), (43.1938, 76.8428), (43.1742, 76.8428),  # Момышулы — 8

    (43.2672, 76.7974), (43.2672, 76.815475), (43.2672, 76.83355), (43.2672, 76.851625),
    (43.2672, 76.8697), (43.2672, 76.887775), (43.2672, 76.90585), (43.2672, 76.923925),
    (43.2672, 76.942), (43.2671, 76.9575),  # Райымбека — 10

    (43.2454, 76.7987), (43.2454, 76.817025), (43.2454, 76.83535), (43.2453, 76.853675),
    (43.2453, 76.872), (43.2453, 76.890325), (43.2453, 76.90865), (43.2452, 76.926975),
    (43.2452, 76.9453), (43.2452, 76.9569),  # Жандосова — 10

    (43.2352, 76.8013), (43.2352, 76.81872), (43.2352, 76.83614), (43.2352, 76.85356),
    (43.2352, 76.87098), (43.2352, 76.8884), (43.2352, 76.90582), (43.2352, 76.92324),
    (43.2352, 76.94066), (43.2352, 76.9585),  # Тимирязева — 10
]


# === ИНИЦИАЛИЗАЦИЯ ===
os.makedirs(SAVE_DIR, exist_ok=True)

# CSV: создать заголовки, если нет
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "lat", "lon", "currentSpeed", "freeFlowSpeed", "confidence"])

# SQLite: создать таблицу
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS traffic (
        timestamp TEXT,
        lat REAL,
        lon REAL,
        currentSpeed REAL,
        freeFlowSpeed REAL,
        confidence REAL
    )
""")
conn.commit()

def log_error(message):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(SAVE_DIR, "error.log"), "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


# === ЗАПРОС ===
def fetch_segment_data(lat, lon):
    url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    params = {
        "point": f"{lat},{lon}",
        "unit": "KMPH",
        "key": API_KEY,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# === УДАЛЕНИЕ СТАРЫХ JSON ===
def cleanup_old_json():
    now = time.time()
    for fname in os.listdir(SAVE_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(SAVE_DIR, fname)
            if os.path.isfile(fpath):
                mtime = os.path.getmtime(fpath)
                if (now - mtime) > RETENTION_DAYS * 86400:
                    os.remove(fpath)

# === ЦИКЛ ===
counter = 1
while True:
    for lat, lon in LOCATIONS:
        try:
            data = fetch_segment_data(lat, lon)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            filename = os.path.join(SAVE_DIR, f"traffic_{timestamp}_{counter}.json")

            # JSON
            with open(filename, "w", encoding="utf-8") as f_json:
                json.dump(data, f_json, ensure_ascii=False, indent=2)

            # CSV
            seg = data["flowSegmentData"]
            row = [
                timestamp,
                lat,
                lon,
                seg.get("currentSpeed"),
                seg.get("freeFlowSpeed"),
                seg.get("confidence"),
            ]
            with open(CSV_FILE, "a", newline="", encoding="utf-8") as f_csv:
                writer = csv.writer(f_csv)
                writer.writerow(row)

            # SQLite
            cursor.execute("""
                INSERT INTO traffic (timestamp, lat, lon, currentSpeed, freeFlowSpeed, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, row)
            conn.commit()

            print(f"[{counter}] ✅ Сохранено: {filename}")
            counter += 1
            time.sleep(INTERVAL_SECONDS)

        except Exception as e:
            error_text = f"[{counter}] ❌ Ошибка на точке ({lat}, {lon}): {e}"
            print(error_text)
            log_error(error_text)
            time.sleep(5)

    cleanup_old_json()

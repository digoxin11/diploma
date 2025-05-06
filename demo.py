import os
import json
import random
from pathlib import Path

# Папка с исходными GeoJSON
input_dir = Path("almaty_traffic_segmented")
output_dir = Path("almaty_traffic_segmented_realistic")
output_dir.mkdir(parents=True, exist_ok=True)

def classify_road(feature):
    name_raw = feature["properties"].get("name", "")
    name = name_raw[0].lower() if isinstance(name_raw, list) and name_raw else str(name_raw).lower()
    highway = feature["properties"].get("highway", "")
    if any(key in name for key in ["абая", "райымбек", "толеби", "сейфуллин", "аль-фараби"]):
        return "central"
    elif highway in ["primary", "secondary", "tertiary"]:
        return "medium"
    else:
        return "peripheral"

def simulate_speed(road_class, hour):
    ffs = random.uniform(30, 50) if road_class == "central" else random.uniform(40, 60) if road_class == "medium" else random.uniform(50, 70)

    if hour in range(7, 10) or hour in range(17, 20):
        ratio = {"central": random.uniform(0.25, 0.55),
                 "medium": random.uniform(0.4, 0.75),
                 "peripheral": random.uniform(0.6, 0.9)}[road_class]
    elif hour in range(12, 14):
        ratio = random.uniform(0.7, 0.9)
    elif hour in range(0, 6) or hour in range(22, 24):
        ratio = random.uniform(0.9, 1.1)
    else:
        ratio = random.uniform(0.8, 1.0)

    speed = max(5, min(ffs * ratio, ffs))
    return round(speed, 1), round(ffs, 1)

# Обработка всех 24 часов
for hour in range(24):
    filename = f"almaty_traffic_segmented_{hour:02}.geojson"
    path = input_dir / filename

    if not path.exists():
        print(f"⛔ Пропущено: {filename} не найден")
        continue

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data["features"]:
        road_class = classify_road(feature)
        speed, ffs = simulate_speed(road_class, hour)
        feature["properties"]["speed_kmph"] = speed
        feature["properties"]["freeFlowSpeed"] = ffs

    out_path = output_dir / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"✅ Сгенерировано: {filename}")



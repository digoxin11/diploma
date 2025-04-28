import pandas as pd
import pydeck as pdk
import glob
import os
import json
import numpy as np
from scipy.spatial import KDTree
from datetime import datetime

# === Настройки ===
DATA_FOLDER = "./diploma"  # Папка с JSON файлами
FILE_PATTERN = "*.json"
MAX_DISTANCE_METERS = 70
MAX_LINES_PER_FRAME = 500
SKIP_FRAMES = 3

# === Загрузка данных ===
def load_data(folder, pattern):
    files = glob.glob(f"{folder}/{pattern}")
    data_list = []
    for file in sorted(files):
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            filename = os.path.basename(file)
            time_part = filename.split('_')[1]
            time_part = time_part.replace('Z', '')
            timestamp = pd.to_datetime(time_part, format='%Y%m%dT%H%M%S', errors='coerce')
            data['timestamp'] = timestamp
            data_list.append(data)
    return data_list

# === Преобразование в DataFrame ===
def extract_to_dataframe(data_list):
    records = []
    for snapshot in data_list:
        timestamp = snapshot.get('timestamp', None)
        flow = snapshot.get('flowSegmentData', None)
        if flow:
            coords = flow.get('coordinates', {}).get('coordinate', [])
            for coord in coords:
                records.append({
                    'timestamp': timestamp,
                    'latitude': coord.get('latitude', None),
                    'longitude': coord.get('longitude', None),
                    'currentSpeed': flow.get('currentSpeed', None),
                    'freeFlowSpeed': flow.get('freeFlowSpeed', None),
                    'travelTime': flow.get('currentTravelTime', None),
                    'freeFlowTravelTime': flow.get('freeFlowTravelTime', None),
                    'confidence': flow.get('confidence', None)
                })
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# === Функция расчёта расстояния ===
def haversine(lon1, lat1, lon2, lat2):
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

# === Построение карты pydeck ===
def create_pydeck_map(df):
    df = df.dropna(subset=['latitude', 'longitude', 'timestamp'])
    grouped = list(df.groupby('timestamp'))

    all_lines = []

    for idx, (timestamp, group) in enumerate(grouped):
        if idx % SKIP_FRAMES != 0:
            continue

        coords = group[['longitude', 'latitude']].values
        if len(coords) < 2:
            continue

        speeds = group['currentSpeed'].values

        tree = KDTree(np.deg2rad(group[['latitude', 'longitude']]))

        for idx, (lon1, lat1) in enumerate(coords):
            dists, idxs = tree.query(np.deg2rad([lat1, lon1]), k=5)
            for j in np.atleast_1d(idxs):
                if j == idx or j >= len(coords):
                    continue

                lon2, lat2 = coords[j]
                distance = haversine(lon1, lat1, lon2, lat2)

                if distance > MAX_DISTANCE_METERS:
                    continue

                speed_avg = np.nanmean([speeds[idx], speeds[j]])

                if np.isnan(speed_avg):
                    continue

                color = [0, 255, 0] if speed_avg >= 40 else ([255, 165, 0] if speed_avg >= 20 else [255, 0, 0])

                all_lines.append({
                    'path': [[lon1, lat1], [lon2, lat2]],
                    'color': color,
                    'timestamp': timestamp
                })

                if len(all_lines) >= MAX_LINES_PER_FRAME * len(grouped):
                    break
            if len(all_lines) >= MAX_LINES_PER_FRAME * len(grouped):
                break

    layer = pdk.Layer(
        "PathLayer",
        data=all_lines,
        get_path="path",
        get_color="color",
        width_scale=20,
        width_min_pixels=2,
        pickable=True
    )

    view_state = pdk.ViewState(
        latitude=43.238949,
        longitude=76.889709,
        zoom=12,
        pitch=45
    )

    deck = pdk.Deck(layers=[layer], initial_view_state=view_state, map_style='mapbox://styles/mapbox/light-v9')
    output_file = f"traffic_pydeck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    deck.to_html(output_file)

    print(f"\n✅ Карта pydeck сохранена в {output_file}\n")

# === Главный блок ===
def main():
    print("\n🚀 Загружаем данные...")
    raw_data = load_data(DATA_FOLDER, FILE_PATTERN)
    print(f"Загружено файлов: {len(raw_data)}")

    print("\n📋 Формируем таблицу...")
    df = extract_to_dataframe(raw_data)
    print(f"Всего точек: {len(df)}")

    print("\n🛠 Строим карту через pydeck...")
    create_pydeck_map(df)

if __name__ == "__main__":
    main()
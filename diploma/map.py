import pandas as pd
import folium
import json
import glob
import os
import numpy as np
from scipy.spatial import KDTree
from folium.plugins import TimestampedGeoJson

# === Настройки ===
DATA_FOLDER = "./diploma"  # Папка, где твои JSON/CSV файлы
FILE_PATTERN = "*.json"  # Или поменяй на "*.csv"
MAX_DISTANCE_METERS = 70  # Максимальное расстояние для соединения точек

# === Загрузка данных ===
def load_data(folder, pattern):
    files = glob.glob(f"{folder}/{pattern}")
    data_list = []
    for file in files:
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

# === Создание карты с чистыми линиями ===
def create_time_map(df, output_file="traffic_map.html"):
    df = df.dropna(subset=['latitude', 'longitude', 'timestamp'])

    coords_rad = np.deg2rad(df[['latitude', 'longitude']])
    tree = KDTree(coords_rad)

    m = folium.Map(location=[43.238949, 76.889709], zoom_start=12)

    grouped = df.groupby('timestamp')

    features = []
    for timestamp, group in grouped:
        coords_list = group[['longitude', 'latitude']].values
        speeds = group['currentSpeed'].values
        times = group['travelTime'].values
        confidences = group['confidence'].values

        for i, (lon1, lat1) in enumerate(coords_list):
            point1 = np.deg2rad([lat1, lon1])
            dist, idx = tree.query(point1, k=5, distance_upper_bound=MAX_DISTANCE_METERS / 6371000)

            for j in np.atleast_1d(idx):
                if j >= len(coords_list) or i == j:
                    continue
                lon2, lat2 = coords_list[j]
                speed_avg = np.nanmean([speeds[i], speeds[j]])
                time_avg = np.nanmean([times[i], times[j]])
                conf_avg = np.nanmean([confidences[i], confidences[j]])

                if np.isnan(speed_avg):
                    continue

                if speed_avg >= 40:
                    color = 'green'
                elif speed_avg >= 20:
                    color = 'orange'
                else:
                    color = 'red'

                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': [
                            [lon1, lat1],
                            [lon2, lat2]
                        ]
                    },
                    'properties': {
                        'time': timestamp.isoformat(),
                        'style': {
                            'color': color,
                            'weight': 5,
                            'opacity': 0.9
                        },
                        'popup': f"<b>Speed:</b> {speed_avg:.1f} km/h<br><b>TravelTime:</b> {time_avg:.1f} sec<br><b>Confidence:</b> {conf_avg:.2f}"
                    }
                }
                features.append(feature)

    TimestampedGeoJson({
        'type': 'FeatureCollection',
        'features': features
    },
    period='PT5M',
    add_last_point=False,
    auto_play=True,
    loop=True
    ).add_to(m)

    m.save(output_file)
    print(f"Карта сохранена в {output_file}")

# === Главный блок ===
def main():
    print("Загружаем данные...")
    raw_data = load_data(DATA_FOLDER, FILE_PATTERN)
    print(f"Загружено {len(raw_data)} файлов")

    print("Формируем таблицу...")
    df = extract_to_dataframe(raw_data)

    print("Создаём карту...")
    create_time_map(df)

if __name__ == "__main__":
    main()
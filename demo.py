import osmnx as ox
import geopandas as gpd
import shapely
from shapely.geometry import LineString
import random
from datetime import datetime, timedelta
from pathlib import Path

# Настройки
city_name = "Almaty, Kazakhstan"
segment_length = 75  # метров
output_dir = Path("almaty_traffic_segmented")
output_dir.mkdir(exist_ok=True)

# Получаем границы города
boundary = ox.geocode_to_gdf(city_name)
graph = ox.graph_from_polygon(boundary.geometry[0], network_type='drive')
edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)

# Фильтрация дорог
valid_types = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential']
edges = edges[edges['highway'].apply(lambda x: any(t in valid_types for t in (x if isinstance(x, list) else [x])))]

edges = edges[['geometry', 'name', 'length']].reset_index(drop=True)

# ✂ Функция разбиения LineString
def split_line(line, max_len):
    if line.length <= max_len:
        return [line]
    segments = []
    current = 0.0
    while current < line.length:
        end = min(current + max_len, line.length)
        segment = shapely.ops.substring(line, current, end)
        segments.append(segment)
        current = end
    return segments

# Разбиваем все улицы на сегменты
print("📏 Разбиваем улицы на короткие участки...")
split_geoms = []
for idx, row in edges.iterrows():
    geom = row.geometry
    name = row.get('name', 'noname')
    try:
        pieces = split_line(geom, segment_length / 111000)  # перевод метров в градусы
        for p in pieces:
            split_geoms.append({'geometry': p, 'name': name})
    except Exception:
        continue

segmented = gpd.GeoDataFrame(split_geoms, crs="EPSG:4326")

# Модель генерации скорости
def generate_speed(hour, length_m):
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        base = random.uniform(8, 20)
    elif 10 <= hour <= 16:
        base = random.uniform(25, 40)
    else:
        base = random.uniform(40, 60)
    noise = random.uniform(-5, 5)
    return round(max(5, min(70, base + noise - length_m / 100)), 1)

# Временные слои
start_time = datetime(2025, 5, 2, 0, 0)
time_steps = [start_time + timedelta(hours=h) for h in range(24)]

# Генерация файлов
print("🚦 Генерируем 24 слоя...")
for ts in time_steps:
    hour = ts.hour
    df = segmented.copy()
    df['timestamp'] = ts.strftime('%Y-%m-%d %H:%M:%S')
    df['length'] = df.geometry.length * 111000  # градусы в метры
    df['speed_kmph'] = df['length'].apply(lambda l: generate_speed(hour, l))
    df['freeFlowSpeed'] = df['speed_kmph'] * random.uniform(1.15, 1.25)
    out_file = output_dir / f"almaty_traffic_segmented_{hour:02}.geojson"
    df[['timestamp', 'name', 'length', 'speed_kmph', 'freeFlowSpeed', 'geometry']].to_file(out_file, driver="GeoJSON")

print("✅ Готово! 24 сегментированных GeoJSON сохранены в almaty_traffic_segmented/")

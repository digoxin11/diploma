import osmnx as ox
import geopandas as gpd
import momepy
import random
from datetime import datetime, timedelta
from pathlib import Path

# Город и параметры
city_name = "Almaty, Kazakhstan"
segment_length = 75  # метров
output_dir = Path("almaty_traffic_segmented")
output_dir.mkdir(exist_ok=True)

# Получаем границы города
boundary = ox.geocode_to_gdf(city_name)

# Скачиваем уличную сеть
graph = ox.graph_from_polygon(boundary.geometry[0], network_type='drive')
edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)

# Фильтруем по типу дорог
valid_highways = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential']
edges = edges[edges['highway'].apply(lambda x: any(h in valid_highways for h in (x if isinstance(x, list) else [x])))]

# Оставляем нужные поля
edges = edges[['geometry', 'name', 'length']].reset_index()

# Разбиваем на отрезки
print("📏 Разбиваем улицы на подотрезки...")
segmented = momepy.segmentize_geometry(edges, max_length=segment_length)

# Временные интервалы (24 часа)
start_time = datetime(2025, 5, 2, 0, 0)
time_steps = [start_time + timedelta(hours=h) for h in range(24)]

# Генератор скорости
def generate_speed(hour, length):
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        base = random.uniform(8, 20)
    elif 10 <= hour <= 16:
        base = random.uniform(25, 40)
    else:
        base = random.uniform(40, 60)
    noise = random.uniform(-5, 5)
    return round(max(5, min(70, base + noise - length / 100)), 1)

# Генерация 24 файлов
print("🚦 Генерируем скорости и сохраняем файлы...")
for ts in time_steps:
    hour = ts.hour
    df = segmented.copy()
    df['timestamp'] = ts.strftime('%Y-%m-%d %H:%M:%S')
    df['length'] = df.geometry.length * 111000  # радиус-земли прибл, чтобы перевести в метры
    df['speed_kmph'] = df['length'].apply(lambda l: generate_speed(hour, l))
    df['freeFlowSpeed'] = df['speed_kmph'] * random.uniform(1.15, 1.25)
    output_file = output_dir / f"almaty_traffic_segmented_{hour:02}.geojson"
    df[['timestamp', 'length', 'speed_kmph', 'freeFlowSpeed', 'geometry']].to_file(output_file, driver="GeoJSON")

print("✅ Готово: сегментированные данные сохранены в almaty_traffic_segmented/")

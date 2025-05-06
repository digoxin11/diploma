import os
import pandas as pd
import osmnx as ox
import geopandas as gpd
from shapely.geometry import LineString
from sklearn.neighbors import BallTree
import numpy as np

# 📁 Путь к папке с CSV-файлами
DATA_DIR = "traffic_data"
OUTPUT_DIR = "almaty_traffic_segmented_realistic"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 🌐 Загружаем уличную сеть Алматы
print("📦 Загружаем улицы Алматы...")
graph = ox.graph_from_place("Almaty, Kazakhstan", network_type="drive")
edges = ox.graph_to_gdfs(graph, nodes=False)
edges = edges.explode(index_parts=False).reset_index(drop=True)
edges["length"] = edges.geometry.length
edges = edges[edges["length"] > 100]  # фильтруем короткие

# ⚙️ Обработка каждого часа
for hour in range(24):
    print(f"⏳ Обработка часа {hour:02d}:00")

    # Загружаем CSV
    csv_path = os.path.join(DATA_DIR, f"traffic_{hour:02d}.csv")
    df = pd.read_csv(csv_path)

    # Построим дерево ближайших точек
    coords_rad = np.deg2rad(df[["lat", "lon"]].values)
    tree = BallTree(coords_rad, metric='haversine')

    # Готовим сегменты
    segments = []

    for _, row in edges.iterrows():
        line = row.geometry
        if line.geom_type != "LineString":
            continue
        mid = line.interpolate(0.5, normalized=True)
        mid_rad = np.deg2rad([[mid.y, mid.x]])

        dist, idx = tree.query(mid_rad, k=3)
        nearby = df.iloc[idx[0]]

        current = nearby["currentSpeed"].mean()
        freeflow = nearby["freeFlowSpeed"].mean()

        segments.append({
            "geometry": line,
            "speed_kmph": current,
            "freeFlowSpeed": freeflow,
            "name": row.get("name", "unknown")
        })

    # Сохраняем в GeoJSON
    gdf = gpd.GeoDataFrame(segments, crs="EPSG:4326")
    out_path = os.path.join(OUTPUT_DIR, f"almaty_traffic_segmented_{hour:02d}.geojson")
    gdf.to_file(out_path, driver="GeoJSON")
    print(f"✅ Сохранено: {out_path}")

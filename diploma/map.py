import pandas as pd
import folium
from folium.plugins import TimestampedGeoJson
import os

# Путь к файлам
csv_path = "diploma/traffic_data.csv"
map_path = "diploma/index.html"

# Загрузка CSV
df = pd.read_csv(csv_path)

# Берём только последние записи (например, 100)
df = df.tail(100)

# Базовая карта Алматы
m = folium.Map(location=[43.238949, 76.889709], zoom_start=12)

# Добавим точки
for _, row in df.iterrows():
    color = "green"
    if row["currentSpeed"] < row["freeFlowSpeed"] * 0.7:
        color = "orange"
    if row["currentSpeed"] < row["freeFlowSpeed"] * 0.4:
        color = "red"

    popup = f"{row['timestamp']}<br>Speed: {row['currentSpeed']} km/h<br>Free: {row['freeFlowSpeed']} km/h"
    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=popup,
    ).add_to(m)

# Сохранение карты
m.save(map_path)
print(f"✅ Карта сохранена: {map_path}")

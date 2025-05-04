import pandas as pd
import glob
import os
import json
import numpy as np
from datetime import datetime
import osmnx as ox

# === Настройки ===
DATA_FOLDER = "./diploma"
FILE_PATTERN = "*.json"
OUTPUT_FOLDER = "./output"
CITY_NAME = "Almaty, Kazakhstan"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Загрузка данных ===
def load_data(folder, pattern):
    files = glob.glob(f"{folder}/{pattern}")
    data_list = []
    for file in sorted(files):
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            filename = os.path.basename(file)
            time_part = filename.split('_')[1].replace('Z', '')
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
                    'confidence': flow.get('confidence', None)
                })
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"DataFrame loaded: {df.shape[0]} rows")
    return df

# === Привязка к ближайшим улицам ===
def assign_nearest_streets(df, graph):
    df = df.dropna(subset=['latitude', 'longitude']).copy()
    nearest_edges = ox.distance.nearest_edges(graph, X=df['longitude'].values, Y=df['latitude'].values)
    df['street_edge'] = [f"{u}-{v}" for u, v, _ in nearest_edges]
    return df

# === Экспорт данных для deck.gl timeline ===
def export_geojson_for_deck(df):
    df = df.sort_values(by='timestamp')
    grouped = df.groupby('street_edge')
    features = []
    timestamp_list = []
    for edge_id, group in grouped:
        group = group.sort_values(by='timestamp').reset_index(drop=True)
        coords = group[['longitude', 'latitude']].values
        speeds = group['currentSpeed'].fillna(0).values
        timestamps = (group['timestamp'].astype(np.int64) // 10**9).astype(int)
        timestamp_list.extend(timestamps)
        for i in range(1, len(coords)):
            line = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [coords[i - 1][0], coords[i - 1][1]],
                        [coords[i][0], coords[i][1]]
                    ]
                },
                "properties": {
                    "speed": float((speeds[i - 1] + speeds[i]) / 2),
                    "timestamp": int(timestamps[i])
                }
            }
            features.append(line)
    print(f"Exported {len(features)} features with {len(set(timestamp_list))} unique timestamps")
    geojson = {"type": "FeatureCollection", "features": features}
    with open(os.path.join(OUTPUT_FOLDER, "data.json"), "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

# === Генерация HTML (leaflet + deck.gl) ===
def generate_html_with_timeline():
    html_content = r'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Traffic Timeline</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/deck.gl@8.9.25/dist.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@deck.gl/leaflet@1.0.8/dist.min.js"></script>
    <style>
        body { margin: 0; overflow: hidden; font-family: sans-serif; }
        #map { position: absolute; width: 100%; height: 100%; }
        #controls {
            position: absolute; bottom: 20px; width: 100%;
            text-align: center; z-index: 1000; color: black;
        }
        #timeSlider { width: 60%; }
        button { padding: 10px 20px; margin-left: 10px; }
        #timestampDisplay { margin: 10px auto; font-size: 16px; }
    </style>
</head>
<body>
<div id="map"></div>
<div id="controls">
    <div id="timestampDisplay">Timestamp: --</div>
    <input type="range" min="0" max="100" value="0" id="timeSlider">
    <button onclick="togglePlay()" id="playBtn">Play</button>
</div>
<script>
let allData = [];
let timestamps = [];
let currentIndex = 0;
let timer = null;

function formatUnixTime(ts) {
    const d = new Date(ts * 1000);
    return d.toISOString().replace('T', ' ').split('.')[0];
}

fetch('data.json')
    .then(resp => resp.json())
    .then(geojson => {
        allData = geojson.features;
        timestamps = [...new Set(allData.map(f => Number(f.properties.timestamp)))].sort((a,b)=>a-b);
        initMap();
    });

function initMap() {
    const slider = document.getElementById('timeSlider');
    const timestampLabel = document.getElementById('timestampDisplay');

    const leafletMap = L.map('map').setView([43.25, 76.89], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(leafletMap);

    const deckLayer = new deck.leaflet.DeckLayer({
        views: new deck.MapView({ repeat: true }),
        layers: []
    });
    deckLayer.addTo(leafletMap);

    slider.max = timestamps.length - 1;

    function updateLayer(index) {
        currentIndex = index;
        const ts = timestamps[index];
        timestampLabel.textContent = "Timestamp: " + formatUnixTime(ts);
        const visible = allData.filter(f => Number(f.properties.timestamp) === Number(ts));
        const layer = new deck.GeoJsonLayer({
            id: 'traffic-layer',
            data: { type: 'FeatureCollection', features: visible },
            getPath: d => d.geometry.coordinates,
            getColor: d => {
                const s = d.properties.speed || 0;
                return [255 - s * 5, s * 5, 150];
            },
            getWidth: 3,
            pickable: true
        });
        deckLayer.setProps({ layers: [layer] });
    }

    slider.oninput = () => updateLayer(parseInt(slider.value));
    updateLayer(0);

    window.togglePlay = function () {
        const btn = document.getElementById('playBtn');
        if (timer) {
            clearInterval(timer);
            timer = null;
            btn.textContent = 'Play';
        } else {
            timer = setInterval(() => {
                currentIndex = (currentIndex + 1) % timestamps.length;
                slider.value = currentIndex;
                updateLayer(currentIndex);
            }, 800);
            btn.textContent = 'Pause';
        }
    }
}
</script>
</body>
</html>
    '''
    with open(os.path.join(OUTPUT_FOLDER, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

# === Главный блок ===
def main():
    print("Loading data...")
    raw_data = load_data(DATA_FOLDER, FILE_PATTERN)
    df = extract_to_dataframe(raw_data)

    print("Downloading OSM graph for Almaty...")
    graph = ox.graph_from_place(CITY_NAME, network_type='drive')

    print("Assigning nearest streets...")
    df = assign_nearest_streets(df, graph)

    print("Exporting data for deck.gl timeline...")
    export_geojson_for_deck(df)

    print("Generating interactive timeline map...")
    generate_html_with_timeline()

    print("Dashboard saved to output/index.html")
    print("Open it via: python -m http.server --directory output")

if __name__ == "__main__":
    main()
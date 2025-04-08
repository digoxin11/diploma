import osmnx as ox
import json

streets = ["Саина", "Аль-Фараби", "Толе Би", "Абая", "Рыскулова", "Момышулы", "Райымбека"]
graph = ox.graph_from_place("Almaty, Kazakhstan", network_type="drive")
edges = ox.graph_to_gdfs(graph, nodes=False)

street_coords = {}
for street in streets:
    matching = edges[edges["name"].astype(str).str.contains(street, case=False, na=False)]
    coords = []
    for line in matching["geometry"]:
        coords.extend(list(line.coords))
    if coords:
        street_coords[street] = coords

# Запись результатов в файл
with open("almaty_street_coords.json", "w", encoding="utf-8") as f:
    json.dump(street_coords, f, indent=2, ensure_ascii=False)

print("Координаты улиц сохранены в almaty_street_coords.json")

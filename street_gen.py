import requests
import json
import math

def haversine(lat1, lon1, lat2, lon2):
    """
    Расчёт расстояния между двумя точками по формуле Хаверсина.
    Возвращает расстояние в метрах.
    """
    R = 6371000  # радиус Земли в метрах
    try:
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
    except ValueError as e:
        raise ValueError(f"Ошибка преобразования координат: {lat1}, {lat2}") from e
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_coord_pair(pair):
    """
    Проверяет, можно ли преобразовать оба элемента пары в float.
    Если нет – предполагаем, что пара не является стандартной координатой [lat, lon].
    """
    try:
        float(pair[0])
        float(pair[1])
        return True
    except ValueError:
        return False

def interpolate_coords(coords, step=10):
    """
    Разбивает последовательность координат (список, где каждый элемент – [lat, lon])
    на отрезки длиной ~step (в метрах).

    Если данные уже имеют формат сегментов (например, первый элемент – dict с ключом "start")
    или первая пара координат не является числовой, то функция возвращает данные как есть.
    """
    if coords:
        # Если элементы уже словари с ключами "start" и "end", пропускаем интерполяцию
        if isinstance(coords[0], dict) and "start" in coords[0]:
            print("Входные данные уже содержат сегменты – пропускаем интерполяцию.")
            return coords
        # Если первая пара не является числовой, тоже пропускаем интерполяцию
        if not is_coord_pair(coords[0]):
            print("Первая пара координат не является числовой – пропускаем интерполяцию.")
            return coords

    segments = []
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        try:
            segment_distance = haversine(lat1, lon1, lat2, lon2)
        except ValueError as e:
            print(f"Ошибка при расчёте расстояния для координат {coords[i]} и {coords[i+1]}: {e}")
            continue
        if segment_distance < step:
            continue
        n_steps = int(segment_distance // step)
        if n_steps == 0:
            continue
        for j in range(n_steps):
            t1 = j / n_steps
            t2 = (j + 1) / n_steps
            start_lat = lat1 + t1 * (lat2 - lat1)
            start_lon = lon1 + t1 * (lon2 - lon1)
            end_lat = lat1 + t2 * (lat2 - lat1)
            end_lon = lon1 + t2 * (lon2 - lon1)
            segments.append({
                "start": [start_lat, start_lon],
                "end": [end_lat, end_lon]
            })
    return segments

def main():
    # Overpass API-запрос для получения всех объектов с тегом "highway" в области Алматы.
    overpass_query = """
    [out:json][timeout:60];
    area["name"="Алматы"]->.searchArea;
    (
      way["highway"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """
    url = "http://overpass-api.de/api/interpreter"
    
    print("Отправка запроса к Overpass API...")
    response = requests.post(url, data={'data': overpass_query})
    data = response.json()
    print("Данные получены.")

    # Собираем все ноды в словарь: {node_id: (lat, lon)}
    nodes = {}
    for elem in data.get('elements', []):
        if elem['type'] == 'node':
            nodes[elem['id']] = (elem['lat'], elem['lon'])
    
    # Результирующий словарь: ключ – название улицы, значение – список сегментов.
    streets_segments = {}

    # Обрабатываем объекты типа "way"
    for elem in data.get('elements', []):
        if elem['type'] != 'way':
            continue
        tags = elem.get('tags', {})
        # Используем только объекты с тегом "name"
        if 'name' not in tags:
            continue
        street_name = tags['name']
        node_ids = elem.get('nodes', [])
        coords = []
        for nid in node_ids:
            if nid in nodes:
                coords.append(nodes[nid])
        if len(coords) < 2:
            continue
        
        segments = interpolate_coords(coords, step=10)
        if not segments:
            continue
        # Если для этой улицы уже есть сегменты, объединяем их
        if street_name in streets_segments:
            streets_segments[street_name].extend(segments)
        else:
            streets_segments[street_name] = segments

    # Сохраняем результат в JSON-файл
    output_filename = "almaty_streets_10m.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(streets_segments, f, ensure_ascii=False, indent=2)
    print(f"Генерация JSON завершена. Результат сохранён в файл '{output_filename}'.")

if __name__ == "__main__":
    main()

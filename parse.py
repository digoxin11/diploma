import os
import time
import math
import csv
import json
import io
import urllib.parse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service 
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image

# ========= Функции для преобразования координат =========

def geo_to_pixel(geo, center, resolution, window_size, upscale=1):
    """
    Преобразует геокоординату (lat, lon) в позицию (x, y) на экране.
    center: текущий центр карты (lat, lon) соответствует точке (window_size/2, window_size/2)
    resolution: исходное разрешение карты в м/пиксель
    upscale: коэффициент масштабирования изображения
    Используем упрощённую модель:
        dx (м) = (lon - center_lon) * (111000 * cos(center_lat))
        dy (м) = (lat - center_lat) * 111000
        x = window_size/2 + dx/resolution
        y = window_size/2 - dy/resolution   (так как ось y растёт вниз)
    После чего умножаем координаты на upscale.
    """
    center_lat, center_lon = center
    lat, lon = geo
    dx_m = (lon - center_lon) * (111000 * math.cos(math.radians(center_lat)))
    dy_m = (lat - center_lat) * 111000
    x = window_size / 2 + dx_m / resolution
    y = window_size / 2 - dy_m / resolution
    return (x * upscale, y * upscale)

def compute_midpoint(start, end):
    """Вычисляет среднюю точку между двумя координатами (lat, lon)."""
    return ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)

# ========= Функции для анализа изображения =========

def sample_line_color(image, p0, p1, num_samples=50):
    """
    Выбирает num_samples точек равномерно вдоль линии между p0 и p1 (пиксели)
    и возвращает средний цвет как (R, G, B).
    """
    x0, y0 = p0
    x1, y1 = p1
    total_r = total_g = total_b = 0
    for i in range(num_samples):
        t = i / (num_samples - 1)
        x = x0 + t * (x1 - x0)
        y = y0 + t * (y1 - y0)
        try:
            r, g, b = image.getpixel((int(round(x)), int(round(y))))[:3]
        except Exception:
            continue
        total_r += r
        total_g += g
        total_b += b
    return (total_r/num_samples, total_g/num_samples, total_b/num_samples)

def compute_line_traffic_level(avg_color):
    """
    На основе среднего цвета вычисляет уровень трафика по шкале 1–10.
    Чем больше зелёного относительно красного, тем выше уровень (10 – свободное движение).
    """
    avg_R, avg_G, _ = avg_color
    if (avg_R + avg_G) == 0:
        return 1
    ratio = avg_G / (avg_R + avg_G)
    level = round(ratio * 9) + 1
    return level

# ========= Функция для выбора нужного масштаба =========

def compute_bounding_box(segments_data):
    """По данным из JSON вычисляет общий bounding box (min_lat, max_lat, min_lon, max_lon)."""
    min_lat = 90
    max_lat = -90
    min_lon = 180
    max_lon = -180
    for street, segments in segments_data.items():
        for seg in segments:
            if "start" not in seg or "end" not in seg:
                continue
            for pt in seg["start"], seg["end"]:
                lat, lon = pt
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat
                if lon < min_lon:
                    min_lon = lon
                if lon > max_lon:
                    max_lon = lon
    return (min_lat, max_lat, min_lon, max_lon)

def compute_recommended_zoom(bbox, window_size):
    """
    Вычисляет рекомендуемый зум для того, чтобы bounding box полностью поместился в окно.
    Используется соотношение: требуемое разрешение = (diff_lat * 111000) / window_size.
    Затем находят зум по формуле: resolution = (156543.03392*cos(center_lat))/2^zoom.
    Возвращает целый зум.
    """
    min_lat, max_lat, min_lon, max_lon = bbox
    diff_lat = max_lat - min_lat
    desired_resolution = (diff_lat * 111000) / window_size
    center_lat = (min_lat + max_lat) / 2
    numerator = 156543.03392 * math.cos(math.radians(center_lat))
    zoom_exact = math.log(numerator / desired_resolution, 2)
    return int(math.floor(zoom_exact))

# ========= Функция для скрытия лишнего интерфейса =========

def hide_ui(driver):
    js = """
    let style = document.createElement('style');
    style.innerHTML = `
      header, footer, .top-panel, .sidebar, .controls, .search-form, .popup,
      .js-toolbar, .map__ctrl, .map-link, .map__logo, [class*="ToolBar"], [class*="button"],
      .menu, .infobox { display: none !important; }
    `;
    document.head.appendChild(style);
    """
    try:
        driver.execute_script(js)
    except Exception as e:
        print("Ошибка скрытия UI:", e)

# ========= Основной код =========

def main():
    # Загружаем JSON с сегментами
    json_filename = "almaty_streets_10m.json"
    with open(json_filename, "r", encoding="utf-8") as f:
        segments_data = json.load(f)
    
    # Вычисляем bounding box по всем сегментам
    bbox = compute_bounding_box(segments_data)
    print("Bounding box:", bbox)
    center_bbox = ((bbox[0] + bbox[1]) / 2, (bbox[2] + bbox[3]) / 2)
    print("Центр bounding box:", center_bbox)
    
    # Выбираем размер окна (например, 1080x1080) – этот размер используется для скриншота
    WINDOW_SIZE = 1080
    # Вычисляем рекомендуемый зум, чтобы bounding box полностью поместился
    recommended_zoom = compute_recommended_zoom(bbox, WINDOW_SIZE)
    # Если рекомендуемый зум слишком мал (для анализа длинных отрезков может быть недостаточно деталей), можно добавить upscale.
    # Здесь можно подстроить: мы попробуем взять max(recommended_zoom, 12) например.
    ZOOM = max(recommended_zoom, 12)
    print(f"Рекомендуемый зум: {recommended_zoom}, выбранный зум: {ZOOM}")
    
    # Вычисляем исходное разрешение в м/пиксель для выбранного зума и центра bounding box
    resolution = (156543.03392 * math.cos(math.radians(center_bbox[0]))) / (2 ** ZOOM)
    print(f"Исходное разрешение: {resolution:.3f} м/пиксель")
    
    # Чтобы улучшить точность анализа маленьких отрезков, масштабируем (upscale) скриншот
    UPSCALE = 16
    effective_resolution = resolution / UPSCALE  # м/пиксель в увеличенном изображении
    print(f"Эффективное разрешение после upscale: {effective_resolution:.3f} м/пиксель")
    
    # Формируем URL для загрузки карты по центру bounding box
    def build_url(center, zoom):
        lat, lon = center
        return f"https://2gis.kz/almaty?m={lon:.6f}%2C{lat:.6f}%2F{zoom}&traffic"
    
    url = build_url(center_bbox, ZOOM)
    print("Открываем страницу:", url)
    
    # Настройка Selenium
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # для отладки можно отключить headless
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument(f'--window-size={WINDOW_SIZE},{WINDOW_SIZE}')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    driver.get(url)
    # Ждем достаточно времени для полной загрузки карты (все элементы)
    time.sleep(10)
    hide_ui(driver)
    
    # Делаем один скриншот всей карты
    png = driver.get_screenshot_as_png()
    driver.quit()
    img_orig = Image.open(io.BytesIO(png))
    # Масштабируем изображение
    new_size = (WINDOW_SIZE * UPSCALE, WINDOW_SIZE * UPSCALE)
    img = img_orig.resize(new_size, resample=Image.BILINEAR)
    
    # Теперь для каждого сегмента из JSON вычисляем его измерение, используя текущее изображение.
    # Переводим каждую геокоординату в позицию на экране. Здесь считаем, что центр карты = center_bbox.
    measurements = {}  # ключ: сегмент (например, "Улица_индекс"), значение: уровень трафика
    segment_ids = []  # для формирования заголовка CSV
    for street_name, segments in segments_data.items():
        for idx, seg in enumerate(segments):
            if "start" not in seg or "end" not in seg:
                continue
            seg_id = f"{street_name}_{idx}"
            start_coords = seg["start"]
            end_coords = seg["end"]
            # Для каждой точки переводим в пиксельные координаты
            p_start = geo_to_pixel(start_coords, center_bbox, resolution, WINDOW_SIZE, upscale=UPSCALE)
            p_end   = geo_to_pixel(end_coords, center_bbox, resolution, WINDOW_SIZE, upscale=UPSCALE)
            # Взяв среднюю выборку пикселей вдоль линии между p_start и p_end, вычисляем средний цвет
            avg_color = sample_line_color(img, p_start, p_end, num_samples=50)
            traffic_level = compute_line_traffic_level(avg_color)
            measurements[seg_id] = traffic_level
            segment_ids.append(seg_id)
    
    # Фиксируем общий timestamp для этой серии измерений
    ts_ms = int(round(time.time() * 1000))
    
    # Формируем CSV: заголовок будет: timestamp, а затем все сегменты.
    csv_filename = "all_segments_measurements.csv"
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        header = ["timestamp"] + segment_ids
        writer.writerow(header)
        # Одна строка с измерениями
        row = [ts_ms]
        for seg_id in segment_ids:
            row.append(measurements.get(seg_id, "N/A"))
        writer.writerow(row)
    
    print(f"Измерения для {len(segment_ids)} сегментов произведены.")
    print(f"Общий timestamp: {ts_ms}")
    print(f"Данные записаны в '{csv_filename}'.")

if __name__ == '__main__':
    main()

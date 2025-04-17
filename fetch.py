#!/usr/bin/env python3
import os
import time
import json
import argparse
from datetime import datetime

import requests

def fetch_traffic(proxy_url: str, api_key: str, bbox: tuple, zoom: int):
    """
    Выполняет GET-запрос к прокси 2GIS и возвращает распарсенный JSON.
    """
    headers = {
        "X-API-Key": api_key
    }
    params = {
        "bbox": ",".join(map(str, bbox)),
        "zoom": zoom,
        # параметр ts добавляет уникальность запроса, чтобы не получить закэшированный результат
        "ts": int(time.time() * 1000),
    }
    resp = requests.get(proxy_url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

def save_json(data: dict, out_dir: str, count: int):
    """
    Сохраняет ответ в файл вида data/traffic_<timestamp>_<count>.json.
    """
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = os.path.join(out_dir, f"traffic_{ts}_{count}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    p = argparse.ArgumentParser(description="Скачивает данные о пробках из 2GIS Traffic API Proxy")
    p.add_argument("--proxy-url", required=True,
                   help="URL вашего прокси (например http://traffic-proxy.yourdomain.com/2gis/traffic-jams)")
    p.add_argument("--api-key", required=True,
                   help="Ваш демо‑ключ 2GIS")
    p.add_argument("--bbox", default="76.80,43.19,77.18,43.42",
                   help="bounding box: left,bot,right,top (Almaty по умолчанию)")
    p.add_argument("--zoom", type=int, default=12,
                   help="уровень детализации карты (zoom level)")
    p.add_argument("--max-requests", type=int, default=1000,
                   help="максимум запросов (лимит демо‑ключа)")
    p.add_argument("--out-dir", default="data",
                   help="папка для сохранения JSON‑файлов")
    args = p.parse_args()

    bbox = tuple(map(float, args.bbox.split(",")))
    count = 0

    print(f"Старт: {args.max_requests} запросов к {args.proxy_url}")
    while count < args.max_requests:
        try:
            data = fetch_traffic(args.proxy_url, args.api_key, bbox, args.zoom)
            save_json(data, args.out_dir, count+1)
            count += 1
            print(f"[{count}/{args.max_requests}] сохранено в `{args.out_dir}`")
        except Exception as e:
            print(f"Ошибка на запросе #{count+1}: {e}")
            # можно добавить time.sleep(5) и повторить
        # чтобы не спамить слишком быстро (необязательно)
        time.sleep(1)

    print("Готово — достигнут лимит запросов.")

if __name__ == "__main__":
    main()

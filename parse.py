import requests
import time
import io
import json
import math
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from statistics import mean

# Загружаем координаты из файла
with open("almaty_street_coords.json", "r", encoding="utf-8") as f:
    street_paths = json.load(f)

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwTKJsfN_uSxSDpeCWi7A_Gtr9Qo3U23FVObKrZHQiPD_rayxUoOzIXW6BjaKwEl7zI/exec"

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=3000,2000')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(browser, 15)

traffic_data = {}

for name, path in street_paths.items():
    print(f"\n\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0443\u043b\u0438\u0446\u044b: {name}")
    lats, lons = zip(*path)
    center_lat = mean(lats)
    center_lon = mean(lons)

    url = f"https://yandex.kz/maps/162/almaty/?ll={center_lon}%2C{center_lat}&z=17&l=trf"
    browser.get(url)

    try:
        canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
        time.sleep(2.5)
        screenshot = canvas.screenshot_as_png
        image = Image.open(io.BytesIO(screenshot))

        width, height = image.size
        print(f"\u0421\u043a\u0440\u0438\u043d {width}x{height}")

        for idx, (lat, lon) in enumerate(path):
            dx = (lon - center_lon) * 60000
            dy = (center_lat - lat) * 60000
            px = int(width // 2 + dx)
            py = int(height // 2 + dy)

            if 0 <= px < width and 0 <= py < height:
                r, g, b = image.getpixel((px, py))[:3]
                if r > 200 and g < 100:
                    level = 2.0
                elif r > 200 and g > 150:
                    level = 1.5
                elif g > 200 and r < 100:
                    level = 1.0
                else:
                    level = 1.2
            else:
                level = 1.2

            traffic_data[f"{name}_{idx}"] = level

    except Exception as e:
        print(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u043d\u0430 {name}: {e}")

browser.quit()

print("\n\u041e\u0442\u043f\u0440\u0430\u0432\u043a\u0430:")
for segment, value in traffic_data.items():
    print(f"{segment}: {value}")

headers = {'Content-Type': 'application/json'}
response = requests.post(GOOGLE_SCRIPT_URL, headers=headers, json=traffic_data)

print("\u0421\u0442\u0430\u0442\u0443\u0441:", response.status_code)
print("\u041e\u0442\u0432\u0435\u0442:", response.text)
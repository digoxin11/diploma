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

# Загружаем координаты из файла
with open("almaty_street_coords.json", "r", encoding="utf-8") as f:
    street_paths = json.load(f)

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwTKJsfN_uSxSDpeCWi7A_Gtr9Qo3U23FVObKrZHQiPD_rayxUoOzIXW6BjaKwEl7zI/exec"

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(browser, 15)

traffic_data = {}

for name, path in street_paths.items():
    segment_idx = 0
    for lat, lon in path:
        url = f"https://yandex.kz/maps/162/almaty/?ll={lon}%2C{lat}&z=17&l=trf"
        browser.get(url)
        try:
            try:
                canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
            except TimeoutException:
                print(f"Canvas не найден на {name}, пробуем refresh...")
                browser.refresh()
                time.sleep(5)
                canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))

            time.sleep(1.0)
            screenshot = canvas.screenshot_as_png
            image = Image.open(io.BytesIO(screenshot))
            width, height = image.size
            center_x, center_y = width // 2, height // 2
            pixel = image.getpixel((center_x, center_y))
            r, g, b = pixel[:3]

            if r > 200 and g < 100:
                level = 2.0
            elif r > 200 and g > 150:
                level = 1.5
            elif g > 200 and r < 100:
                level = 1.0
            else:
                level = 1.2

            key = f"{name}_{segment_idx}"
            traffic_data[key] = level
            segment_idx += 1
        except Exception as e:
            print(f"Ошибка на {name} [{lat}, {lon}]: {e}")
            traffic_data[f"{name}_{segment_idx}"] = 1.2
            segment_idx += 1

browser.quit()

print("Отправляем следующие данные:")
for segment, value in traffic_data.items():
    print(f"{segment}: {value}")

headers = {'Content-Type': 'application/json'}
response = requests.post(GOOGLE_SCRIPT_URL, headers=headers, json=traffic_data)

print("Статус отправки:", response.status_code)
print("Ответ:", response.text)

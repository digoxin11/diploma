import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import io
import json

# Улицы с координатами сегментов
streets = {
    "Сайна": [43.250, 76.870],
    "Аль-Фараби": [43.234, 76.900],
    "Толе Би": [43.256, 76.870],
    "Абая": [43.244, 76.870],
    "Рыскулова": [43.295, 76.840],
    "Момышулы": [43.220, 76.850],
    "Райымбека": [43.258, 76.870]
}

# URL Google Apps Script Web App
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/library/d/1oTSW7e0ZfYBWmfM_THx0dO6O83uZM0LfgPebUj2qRPJx1ze-NOhuHM26/1"

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1280,800')

browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

traffic_data = {}

for name, (lat, lon) in streets.items():
    url = f"https://yandex.kz/maps/162/almaty/?ll={lon}%2C{lat}&z=15&layer=traffic"
    browser.get(url)
    time.sleep(7)

    try:
        canvas = browser.find_element(By.TAG_NAME, "canvas")
        screenshot = canvas.screenshot_as_png
        image = Image.open(io.BytesIO(screenshot))
        width, height = image.size
        center_x, center_y = width // 2, height // 2
        pixel = image.getpixel((center_x, center_y))
        r, g, b = pixel[:3]

        if r > 200 and g < 100:
            level = 2.0  # красный
        elif r > 200 and g > 150:
            level = 1.5  # оранжевый
        elif g > 200 and r < 100:
            level = 1.0  # зелёный
        else:
            level = 1.2  # неопределённый цвет

        traffic_data[name] = level
    except Exception as e:
        print(f"Ошибка на {name}: {e}")
        traffic_data[name] = 1.2

browser.quit()

headers = {'Content-Type': 'application/json'}
response = requests.post(GOOGLE_SCRIPT_URL, headers=headers, json=traffic_data)

print("Статус отправки:", response.status_code)
print("Ответ:", response.text)

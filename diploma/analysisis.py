import pandas as pd
import matplotlib.pyplot as plt
import json
import glob

# === Настройки ===
DATA_FOLDER = "./diploma"  # Папка, где твои JSON/CSV файлы
FILE_PATTERN = "*.json"  # Или поменяй на "*.csv"

# === Загрузка данных ===
def load_data(folder, pattern):
    files = glob.glob(f"{folder}/{pattern}")
    data_list = []
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
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
            latitude = coords[0]['latitude'] if coords else None
            longitude = coords[0]['longitude'] if coords else None

            records.append({
                'timestamp': timestamp,
                'latitude': latitude,
                'longitude': longitude,
                'currentSpeed': flow.get('currentSpeed', None),
                'freeFlowSpeed': flow.get('freeFlowSpeed', None),
                'travelTime': flow.get('currentTravelTime', None),
                'freeFlowTravelTime': flow.get('freeFlowTravelTime', None),
                'confidence': flow.get('confidence', None)
            })
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# === Построение графиков ===
def plot_speed_over_time(df):
    plt.figure(figsize=(12,6))
    for coord, group in df.groupby(['latitude', 'longitude']):
        plt.plot(group['timestamp'], group['currentSpeed'], label=f"{coord}")
    plt.xlabel('Время')
    plt.ylabel('Скорость (км/ч)')
    plt.title('Изменение скорости на участках')
    plt.legend()
    plt.grid(True)
    plt.show()

# === Статистика ===
def basic_stats(df):
    print("\n=== Базовая статистика по скорости ===")
    print(df[['currentSpeed', 'freeFlowSpeed']].describe())
    print("\n=== Процент задержки ===")
    df['delay_percent'] = 100 * (df['travelTime'] - df['freeFlowTravelTime']) / df['freeFlowTravelTime']
    print(df['delay_percent'].describe())

# === Главный блок ===
def main():
    print("Загружаем данные...")
    raw_data = load_data(DATA_FOLDER, FILE_PATTERN)
    print(f"Загружено {len(raw_data)} файлов")

    print("Формируем таблицу...")
    df = extract_to_dataframe(raw_data)

    print("Анализируем...")
    basic_stats(df)
    plot_speed_over_time(df)

if __name__ == "__main__":
    main()

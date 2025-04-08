#include <WiFi.h>
#include <HTTPClient.h>

// WiFi данные
const char* ssid = "Aiym";
const char* password = "87066055024";

// Адрес твоего Google Apps Script (Web App URL)
const char* script_url = "https://script.google.com/macros/library/d/1oTSW7e0ZfYBWmfM_THx0dO6O83uZM0LfgPebUj2qRPJx1ze-NOhuHM26/1";

// Интервал между отправками (в мс)
const unsigned long interval = 5 * 60 * 1000;
unsigned long lastMillis = 0;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  Serial.print("Подключение к WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" OK");
}

void loop() {
  unsigned long now = millis();
  if (now - lastMillis > interval || lastMillis == 0) {
    lastMillis = now;

    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(script_url);
      http.addHeader("Content-Type", "application/json");

      // Здесь можно заменить значения на реальные (с сенсора, расчёта, парсинга и т.д.)
      String payload = R"rawliteral(
      {
        "Сайна": 1.4,
        "Аль-Фараби": 1.6,
        "Толе Би": 1.2,
        "Абая": 1.5,
        "Рыскулова": 1.7,
        "Момышулы": 1.3,
        "Райымбека": 1.6
      }
      )rawliteral";

      int httpResponseCode = http.POST(payload);
      Serial.print("Ответ от Google: ");
      Serial.println(httpResponseCode);
      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("Ответ: " + response);
      }

      http.end();
    } else {
      Serial.println("WiFi отключён. Повторное подключение...");
      WiFi.begin(ssid, password);
    }
  }

  delay(1000); // базовая задержка
}

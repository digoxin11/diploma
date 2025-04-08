#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

const char* traffic_url = "https://raw.githubusercontent.com/yourusername/traffic-data/main/almaty-traffic.json";
const char* google_webhook_url = "https://script.google.com/macros/s/AKf.../exec"; // вставь свой URL

unsigned long interval = 5 * 60 * 1000;
unsigned long lastCheck = 0;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  Serial.println("WiFi connected.");
}

void loop() {
  unsigned long now = millis();
  if (now - lastCheck >= interval || lastCheck == 0) {
    lastCheck = now;

    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(traffic_url);
      int httpCode = http.GET();

      if (httpCode == 200) {
        String payload = http.getString();
        Serial.println("Traffic JSON: " + payload);

        int idx = payload.indexOf("level");
        int colon = payload.indexOf(":", idx);
        int end = payload.indexOf("}", colon);
        String levelStr = payload.substring(colon + 1, end);
        levelStr.trim();
        int trafficLevel = levelStr.toInt();

        Serial.print("Traffic level: ");
        Serial.println(trafficLevel);

        // Отправляем в Google Sheets
        HTTPClient httpPost;
        httpPost.begin(google_webhook_url);
        httpPost.addHeader("Content-Type", "application/json");

        String jsonPayload = "{\"level\": " + String(trafficLevel) + "}";
        int postCode = httpPost.POST(jsonPayload);
        Serial.print("POST response: ");
        Serial.println(postCode);
        httpPost.end();
      }

      http.end();
    }
  }

  delay(1000);
}

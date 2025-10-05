// src/main.cpp (mock-mode)
#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>

#include "wifi_config.h"

// Use mock sensors if true
#define MOCK_MODE true

// ---------- config (reuse your pins if needed) ----------
#define DHTPIN 15
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

WiFiClient espClient;
PubSubClient mqttClient(espClient);

unsigned long lastPublish = 0;
const unsigned long PUBLISH_INTERVAL = 3000UL; // publish every 3s in mock mode

// random generator helper
float randf(float a, float b){ return a + ((float)random(0,10000)/10000.0f)*(b-a); }

// Simulated state
float sim_temp = 30.0f;
float sim_hum = 45.0f;
float sim_current_mA = 1500.0f;
float sim_voltage = 12.0f;
int sim_vib = 0;

void connectWiFi(){
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("Connecting to WiFi ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long start = millis();
  while (WiFi.status()!=WL_CONNECTED){
    delay(200);
    Serial.print(".");
    if (millis()-start>15000) { Serial.println("\nWiFi failed (mock continues)"); return; }
  }
  Serial.println("\nWiFi connected (mock).");
}

void connectMQTT(){
  if (mqttClient.connected()) return;
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  Serial.print("Connecting MQTT...");
  if (mqttClient.connect(DEVICE_ID)) Serial.println("ok");
  else Serial.println("failed (mock continues)");
}

void showOnOLED(float t,float h,float i,float v,int vib){
  if (!display.begin(SSD1306_SWITCHCAPVCC,0x3C)) return;
  display.clearDisplay();
  display.setTextSize(1); display.setTextColor(SSD1306_WHITE); display.setCursor(0,0);
  display.printf("Device:%s\nT:%.1fC H:%.0f%%\nI:%.0fmA V:%.2fV\nVib:%d\n", DEVICE_ID, t, h, i, v, vib);
  display.display();
}

void setup(){
  Serial.begin(115200);
  delay(200);
  randomSeed(analogRead(0));

  // init simulated sensors only if real ones not available
  if (!MOCK_MODE) dht.begin();
  // init display (optional)
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay(); display.display();

  connectWiFi(); connectMQTT();
  Serial.println("Mock firmware ready.");
}

void publishJSON(float t, float h, int vib, float imA, float vbus){
  char payload[512];
  unsigned long nowS = (unsigned long)(millis()/1000);
  snprintf(payload,sizeof(payload),
    "{\"device_id\":\"%s\",\"ts\":%lu,\"temp_c\":%.2f,\"humidity_pct\":%.2f,"
    "\"vibration\":%d,\"current_mA\":%.2f,\"voltage_v\":%.2f}",
    DEVICE_ID, nowS, t, h, vib, imA, vbus );
  Serial.println(payload);
  if (mqttClient.connected()) mqttClient.publish(MQTT_TOPIC, payload);
}

void loop(){
  if (WiFi.status()!=WL_CONNECTED) connectWiFi();
  if (!mqttClient.connected()) connectMQTT();
  mqttClient.loop();

  unsigned long now = millis();
  if (now - lastPublish >= PUBLISH_INTERVAL){
    lastPublish = now;

    if (MOCK_MODE){
      // random walk + occasional spike
      sim_temp += randf(-0.3, 0.3);
      sim_hum += randf(-0.5, 0.5);
      sim_current_mA += randf(-50, 50);
      sim_voltage += randf(-0.03, 0.03);
      // random vibration event
      sim_vib = (random(0,100) > 95) ? 1 : 0;
      // occasional big spike
      if (random(0,1000) > 985) sim_current_mA *= 3.0f;

      publishJSON(sim_temp, sim_hum, sim_vib, sim_current_mA, sim_voltage);
      showOnOLED(sim_temp, sim_hum, sim_current_mA, sim_voltage, sim_vib);
    } else {
      // real sensor code (left minimal so it builds without hardware)
      float t = dht.readTemperature();
      float h = dht.readHumidity();
      int vib = 0; float i=0.0f, v=0.0f;
      publishJSON(t,h,vib,i,v);
      showOnOLED(t,h,i,v,vib);
    }
  }
  delay(10);
}

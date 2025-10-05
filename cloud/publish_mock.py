#!/usr/bin/env python3
# publish_mock.py
import time, json, random
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "ent/device/ENT_DEV_001/telemetry"

c = mqtt.Client()
c.connect(BROKER, PORT, 60)

print("Publishing mock telemetry to", TOPIC)
while True:
    payload = {
        "device_id": "ENT_DEV_001",
        "ts": int(time.time()),
        "temp_c": 30.0 + random.uniform(-1.5, 1.5),
        "humidity_pct": 45.0 + random.uniform(-3, 3),
        "vibration": 1 if random.random() > 0.97 else 0,
        "current_mA": 1500.0 + random.uniform(-200, 200),
        "voltage_v": 12.0 + random.uniform(-0.2, 0.2)
    }
    c.publish(TOPIC, json.dumps(payload))
    print("Published:", payload)
    time.sleep(3)

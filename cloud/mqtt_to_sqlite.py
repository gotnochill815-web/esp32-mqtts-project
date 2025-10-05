#!/usr/bin/env python3
# mqtt_to_sqlite.py
import json, sqlite3, time
import paho.mqtt.client as mqtt

# Configuration
MQTT_BROKER = "127.0.0.1"   # change to your broker IP if needed
MQTT_PORT = 1883
MQTT_TOPIC = "ent/device/+/telemetry"  # wildcard for all devices
SQLITE_FILE = "telemetry.db"

# Setup DB (file will be created in the current working directory)
conn = sqlite3.connect(SQLITE_FILE, check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER,
    device_id TEXT,
    temp_c REAL,
    humidity_pct REAL,
    vibration INTEGER,
    current_mA REAL,
    voltage_v REAL
)
''')
conn.commit()

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT (rc=%s)" % rc)
    client.subscribe(MQTT_TOPIC)
    print("Subscribed to", MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except Exception as e:
        print("Bad payload:", e, msg.payload)
        return

    ts = int(payload.get("ts", time.time()))
    device_id = payload.get("device_id", "unknown")
    temp_c = payload.get("temp_c", None)
    humidity_pct = payload.get("humidity_pct", None)
    vibration = int(payload.get("vibration", 0))
    current_mA = float(payload.get("current_mA", 0.0))
    voltage_v = float(payload.get("voltage_v", 0.0))

    c.execute('''
      INSERT INTO telemetry (ts, device_id, temp_c, humidity_pct, vibration, current_mA, voltage_v)
      VALUES (?,?,?,?,?,?,?)
    ''', (ts, device_id, temp_c, humidity_pct, vibration, current_mA, voltage_v))
    conn.commit()
    print(f"Saved row for {device_id} @ {ts}")

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    print(f"Connecting to MQTT {MQTT_BROKER}:{MQTT_PORT} ...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()

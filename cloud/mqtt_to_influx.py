# cloud/mqtt_to_sqlite.py
import sqlite3
import paho.mqtt.client as mqtt
import json
import time

# ---------- SQLite setup ----------
conn = sqlite3.connect("device_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    temperature REAL,
    humidity REAL,
    current REAL,
    voltage REAL,
    vibration REAL
)
""")
conn.commit()

# ---------- MQTT setup ----------
BROKER = "broker.hivemq.com"   # or your local Mosquitto broker
TOPIC = "ent-device/data"

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print("Received:", payload)

        cursor.execute("""
            INSERT INTO sensor_data (timestamp, temperature, humidity, current, voltage, vibration)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            payload.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
            payload.get("temperature"),
            payload.get("humidity"),
            payload.get("current"),
            payload.get("voltage"),
            payload.get("vibration")
        ))
        conn.commit()
    except Exception as e:
        print("Error processing message:", e)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, 1883, 60)
client.loop_forever()

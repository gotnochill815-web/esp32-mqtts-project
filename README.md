🌟 DIPLOWER BIT-DRIVE
Smart ESP32 MQTTs Project with Real-time Data Streaming & Cloud Integration

A complete IoT solution that connects ESP32 devices to cloud services through secure MQTT communication, featuring real-time data processing, storage, and visualization.

🚀 What This Project Does
Imagine having smart devices that can talk to each other and share their data securely over the internet! That's exactly what this project enables:

📡 ESP32 Devices collect sensor data and publish it securely via MQTT

☁️ Cloud Scripts receive, process, and store the data in databases

📊 Dashboard lets you visualize your data in real-time

💾 Multiple Storage Options - SQLite for local, InfluxDB for time-series data

🏗️ Project Structure
text
DIPLOWER-BIT-DRIVE/
├── 📁 firmware/           # ESP32 Source Code
│   ├── src/main.cpp      # Main device firmware
│   ├── include/          # Configuration files
│   └── platformio.ini    # Build configuration
├── 📁 cloud/             # Data Processing Scripts
│   ├── mqtt_to_sqlite.py # Stores data in SQLite database
│   ├── mqtt_to_influx.py # Sends data to InfluxDB
│   ├── dashboard.py      # Web interface for data
│   ├── publish_mock.py   # Test data generator
│   └── view_db.py        # Database viewer
└── 📄 Configuration Files
    ├── platformio.ini    # ESP32 build settings
    └── wifi_config.h     # WiFi credentials (template)
🛠️ Quick Start
For ESP32 Development
Setup Environment

bash
# Install PlatformIO (if using VSCode, get the PlatformIO extension)
# Open the firmware folder in PlatformIO
Configure WiFi

cpp
// Copy include/wifi_config.example.h to include/wifi_config.h
// Add your WiFi credentials:
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
Build & Upload

bash
# In PlatformIO, click Build → Upload
# Monitor serial output at 115200 baud
For Cloud Services
Install Dependencies

bash
pip install paho-mqtt sqlite3 influxdb flask
Run Data Processor

bash
# Start storing MQTT data in SQLite
python cloud/mqtt_to_sqlite.py

# Or send to InfluxDB
python cloud/mqtt_to_influx.py

# Launch the web dashboard
python cloud/dashboard.py
Test with Mock Data

bash
python cloud/publish_mock.py
📡 How It Works
Device Side (ESP32)
Connects to WiFi and MQTT broker

Reads sensor data (temperature, humidity, etc.)

Publishes JSON data to MQTT topics

Handles secure TLS connections

Cloud Side (Python)
mqtt_to_sqlite.py: Listens to MQTT and stores in local SQLite database

mqtt_to_influx.py: Forwards data to InfluxDB for time-series analysis

dashboard.py: Provides web interface to view real-time data

view_db.py: Command-line tool to inspect stored data

🔧 Configuration
MQTT Settings
Update these in both firmware and cloud scripts:

python
MQTT_BROKER = "your-broker.com"
MQTT_PORT = 8883
MQTT_TOPIC = "sensors/+/data"
Database Setup
SQLite: Automatically creates telemetry.db
InfluxDB: Update connection details in mqtt_to_influx.py

🎯 Use Cases
Perfect for:

✅ Home Automation - Temperature monitoring, smart devices

✅ Industrial IoT - Equipment monitoring, sensor networks

✅ Research Projects - Data collection and analysis

✅ Learning MQTT - Understanding IoT communication protocols

🐛 Troubleshooting
Device won't connect?

Check WiFi credentials in wifi_config.h

Verify MQTT broker is accessible

Monitor serial output for error messages

Data not appearing?

Ensure cloud scripts are running

Check MQTT topic names match

Verify database connections

Build errors?

Make sure PlatformIO is properly installed

Check all library dependencies

🤝 Contributing
Found a bug? Have an idea? We'd love your help!

Fork the project

Create your feature branch

Commit your changes

Push to the branch

Open a Pull Request

📝 License
This project is open source. Feel free to use it for personal or educational purposes.

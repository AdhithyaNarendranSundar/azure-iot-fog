# 1. multi_device_simulator.py
import time
import threading
import json
import requests
from azure.iot.device import IoTHubDeviceClient, Message
from azure.iot.device.exceptions import ConnectionFailedError, NoConnectionError

API_KEY = "8825007cb988e95d24e21e9ffce75e2a"
SEND_INTERVAL = 5

DEVICE_CONFIG = {

    "device001": {
        "city": "Dublin",
        "lat": 53.3498,
        "lon": -6.2603,
        "conn": "HostName=iotlabhub123xyz.azure-devices.net;DeviceId=device001;SharedAccessKey=z8lNNOjWiEzoD11fO2jWm7qfcOM9OEYz6ecWSSaZKZs="
    },
    "device002": {
        "city": "Chennai",
        "lat": 13.0827,
        "lon": 80.2707,
        "conn": "HostName=iotlabhub123xyz.azure-devices.net;DeviceId=device002;SharedAccessKey=8T0osH8TScP7/xFFLZYmS0P2k5YN2x09aMAvy5LGnZQ="
    }
    ,
    "device003": {
        "city": "Tokyo",
        "lat": 35.6895,
        "lon": 139.6917,
        "conn": "HostName=iotlabhub123xyz.azure-devices.net;DeviceId=device003;SharedAccessKey=yKFZ8Pf0wOY/7xvD5SMWJUd3onQ4LfHKSoq6SjaVQrQ="
    }
}

def fetch_weather(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            print(f"❌ API error: {response.status_code} - {data}")
            return None, None

        temp = round(data["main"]["temp"], 2)
        humidity = round(data["main"]["humidity"], 2)
        return temp, humidity
    except Exception as e:
        print(f"❌ Exception in fetch_weather: {e}")
        return None, None


def send_real_weather(device_id, city, lat, lon, conn_str):
    def connect():
        client = None
        while client is None:
            try:
                client = IoTHubDeviceClient.create_from_connection_string(conn_str)
                client.connect()
                print(f"[{device_id}] ✅ Connected")
            except Exception as e:
                print(f"[{device_id}] ❌ Connect error: {e}")
                time.sleep(5)
        return client

    client = connect()
    while True:
        temperature, humidity = fetch_weather(lat, lon)
        print(f"[{device_id}] 🌡️ Weather fetched: Temp={temperature}, Humidity={humidity}")  # <--- ADD THIS LINE

        if temperature is None:
            time.sleep(SEND_INTERVAL)
            continue

        alert = "HIGH" if temperature > 40 else "NORMAL"
        payload = {
            "device": device_id,
            "city": city,
            "temperature": temperature,
            "humidity": humidity,
            "lat": lat,
            "lon": lon,
            "alert": alert,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            message = Message(json.dumps(payload))
            message.content_type = "application/json"
            message.content_encoding = "utf-8"
            client.send_message(message)
            print(f"[{device_id}] ✅ Sent: {payload}")
        except Exception as e:
            print(f"[{device_id}] ❌ Send failed: {e}. Reconnecting...")
            try: client.shutdown()
            except: pass
            client = connect()

        time.sleep(SEND_INTERVAL)

if __name__ == "__main__":
    for device_id, conf in DEVICE_CONFIG.items():
        t = threading.Thread(
            target=send_real_weather,
            args=(device_id, conf["city"], conf["lat"], conf["lon"], conf["conn"])
        )
        t.daemon = True
        t.start()

    while True:
        time.sleep(10)


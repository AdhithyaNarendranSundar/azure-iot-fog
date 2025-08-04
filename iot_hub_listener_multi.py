# iot_hub_listener_multi.py
import csv
import json
from azure.eventhub import EventHubConsumerClient

EVENT_HUB_CONNECTION_STR = (
    "Endpoint=sb://ihsuprodblres005dednamespace.servicebus.windows.net/;"
    "SharedAccessKeyName=iothubowner;"
    "SharedAccessKey=SUKC2tH6qeVoLCV5nJr0DD7N00OtpJXnzAIoTPVKLC8=;"
    "EntityPath=iothub-ehub-iotlabhub1-66507521-17dc9e08e8"
)
EVENT_HUB_NAME = "iothub-ehub-iotlabhub1-66507521-17dc9e08e8"
CSV_FILE = "telemetry_log.csv"

FIELDNAMES = ["timestamp", "temperature", "humidity", "alert", "device", "city", "lat", "lon"]

def on_event(partition_context, event):
    try:
        data = json.loads(event.body_as_str(encoding='UTF-8'))

        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow({
                "timestamp": data.get("timestamp"),
                "temperature": data.get("temperature"),
                "humidity": data.get("humidity"),
                "alert": data.get("alert"),
                "device": data.get("device"),
                "city": data.get("city"),
                "lat": data.get("lat"),
                "lon": data.get("lon")
            })

        print(f"✅ Received from {data['device']}: {data}")

    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e} | Raw event: {event.body_as_str(encoding='UTF-8')}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == '__main__':
    client = EventHubConsumerClient.from_connection_string(
        conn_str=EVENT_HUB_CONNECTION_STR,
        consumer_group="$Default",
        eventhub_name=EVENT_HUB_NAME
    )
    with client:
        print("📡 Listening to Azure IoT Hub Event Stream...")
        client.receive(on_event=on_event, starting_position="-1")

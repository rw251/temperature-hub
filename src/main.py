import paho.mqtt.client as mqtt
import json
import logging
from math import exp, log
from datetime import datetime
from pathlib import Path
from os import getenv, path
from time import sleep
from tempfile import NamedTemporaryFile

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


data_dir = Path("/data")
if not data_dir.exists():
    data_dir = Path(path.dirname(__file__)) / ".." / "data" / "shared"
segments_dir = data_dir / "segments"
index_file = data_dir / "index.json"
config_file = Path(path.dirname(__file__)) / "config.json"
mqtt_host = getenv("MQTT_HOST", "mosquitto")


def append_reading(
    timestamp, location, device, temperature, humidity, dew_point, battery
):
    segments_dir.mkdir(parents=True, exist_ok=True)
    segment_name = f"{timestamp.date().isoformat()}.tsv"
    segment_path = segments_dir / segment_name
    line = (
        f"{timestamp.isoformat()[0:19]}\t{location}\t{device}\t{temperature}\t"
        f"{humidity}\t{dew_point}\t{battery}\n"
    )

    with open(segment_path, "a") as f:
        f.write(line)

    update_index(segment_name)


def update_index(segment_name):
    try:
        if index_file.exists():
            index = json.loads(index_file.read_text())
        else:
            index = {"version": 1, "segments": []}
    except Exception:
        logging.warning("Rebuilding data index after failing to read it")
        index = {"version": 1, "segments": []}

    segments = sorted({*index.get("segments", []), segment_name})
    write_index(segments)


def write_index(segments):
    data_dir.mkdir(parents=True, exist_ok=True)
    index = {"version": 1, "segments": sorted(segments)}
    with NamedTemporaryFile("w", dir=data_dir, delete=False) as tmp:
        json.dump(index, tmp)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(index_file)
    index_file.chmod(0o644)


def update_index_from_disk():
    segments_dir.mkdir(parents=True, exist_ok=True)
    write_index(segment_path.name for segment_path in segments_dir.glob("*.tsv"))


def on_connect(client, userdata, flags, reason_code, properties):
    if flags.session_present:
        ...
    if reason_code == 0:
        logging.info("Connected to MQTT broker")
        client.subscribe("zigbee2mqtt/dewpoint/#")
        # client.subscribe("zigbee2mqtt/#")
    if reason_code > 0:
        # error processing
        logging.error(f"Failed to connect, result code {reason_code}")


def on_message(client, userdata, msg):
    # print(msg)
    logging.info(f"Received message on topic {msg.topic}")
    if len(msg.payload) > 5:
        data = msg.payload.decode()
        # print(client)
        # print(userdata)
        logging.info(data)
        try:
            items = json.loads(data)
            config = json.loads(config_file.read_text())
            if "humidity" not in items or "temperature" not in items:
                return
            humidity = items["humidity"]
            temperature = items["temperature"]
            battery = items["battery"] if "battery" in items else 0
            dew_point = (
                1
                / (
                    (1 / 273)
                    - log(
                        (0.611 * exp(5423 * ((1 / 273) - (1 / (273 + temperature)))))
                        * humidity
                        / 61.1
                    )
                    / 5423
                )
            ) - 273
            timestamp = datetime.now()
            device = msg.topic.split("/")[-1]
            location = device
            if device in config["mapping"]:
                location = config["mapping"][device]
            append_reading(
                timestamp, location, device, temperature, humidity, dew_point, battery
            )
        except Exception as e:
            logging.error(f"Error processing message on topic {msg.topic}: {e}")


def run():
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    update_index_from_disk()
    while True:
        try:
            logging.info(f"Attempting to connect to MQTT broker at {mqtt_host}:1883...")
            mqttc.connect(mqtt_host, 1883, 60)
            break
        except:
            logging.error("Inital connection failed ... retrying in 5s...")
            sleep(5)
            pass

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    mqttc.loop_forever()


if __name__ == "__main__":
    run()

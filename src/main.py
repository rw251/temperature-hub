import paho.mqtt.client as mqtt
import json
import logging
from math import exp, log
from datetime import datetime
from pathlib import Path
from os import path
from time import sleep

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


data_file = Path(path.dirname(__file__)) / ".." / "data" / "data.txt"
config_file = Path(path.dirname(__file__)) / "config.json"


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
            isoTimeString = datetime.now().isoformat()[0:19]
            device = msg.topic.split("/")[-1]
            location = device
            if device in config["mapping"]:
                location = config["mapping"][device]
            with open(data_file, "a") as f:
                f.write(
                    f"""{isoTimeString}\t{location}\t{device}\t{temperature}\t{humidity}\t{dew_point}\t{battery}\n"""
                )
        except Exception as e:
            logging.error(f"Error processing message on topic {msg.topic}: {e}")


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message
while True:
    try:
        logging.info("Attempting to connect to MQTT broker on port 1883...")
        mqttc.connect("127.0.0.1", 1883, 60)
        break
    except:
        logging.error("Inital connection failed ... retrying in 5s...")
        sleep(5)
        pass

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
mqttc.loop_forever()

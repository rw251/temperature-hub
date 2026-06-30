import logging
import os
import time
from typing import Optional

import docker
import paho.mqtt.client as mqtt


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
WATCH_TOPIC = os.getenv("WATCH_TOPIC", "zigbee2mqtt/dewpoint/+")
TARGET_CONTAINER = os.getenv("TARGET_CONTAINER", "temperature-hub-zigbee2mqtt")
STALE_AFTER_SECONDS = int(os.getenv("STALE_AFTER_SECONDS", str(2 * 60 * 60)))
RESTART_COOLDOWN_SECONDS = int(os.getenv("RESTART_COOLDOWN_SECONDS", str(30 * 60)))
STARTUP_GRACE_SECONDS = int(os.getenv("STARTUP_GRACE_SECONDS", str(15 * 60)))
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))

last_message_at: Optional[float] = None
last_restart_at = 0.0
connected = False


def on_connect(client, userdata, flags, reason_code, properties):
    global connected
    if reason_code == 0:
        connected = True
        logging.info("Connected to MQTT broker; watching %s", WATCH_TOPIC)
        client.subscribe(WATCH_TOPIC)
    else:
        connected = False
        logging.error("Failed to connect to MQTT broker: %s", reason_code)


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    global connected
    connected = False
    logging.warning("Disconnected from MQTT broker: %s", reason_code)


def on_message(client, userdata, msg):
    global last_message_at
    if msg.retain:
        logging.info("Received retained watchdog message on %s", msg.topic)
    else:
        logging.info("Received fresh watchdog message on %s", msg.topic)
    last_message_at = time.monotonic()


def restart_target():
    docker_client = docker.from_env()
    container = docker_client.containers.get(TARGET_CONTAINER)
    logging.warning("Restarting %s after stale sensor readings", TARGET_CONTAINER)
    container.restart(timeout=20)


def main():
    global last_message_at, last_restart_at

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    started_at = time.monotonic()
    while True:
        now = time.monotonic()
        in_grace = now - started_at < STARTUP_GRACE_SECONDS
        in_cooldown = now - last_restart_at < RESTART_COOLDOWN_SECONDS

        if last_message_at is None:
            stale_for = 0.0
        else:
            stale_for = now - last_message_at

        if (
            connected
            and not in_grace
            and not in_cooldown
            and stale_for > STALE_AFTER_SECONDS
        ):
            try:
                restart_target()
                last_restart_at = now
                last_message_at = now
            except Exception:
                logging.exception("Failed to restart %s", TARGET_CONTAINER)

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

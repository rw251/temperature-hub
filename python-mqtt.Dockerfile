FROM python:3.11-slim

# Install git and mosquitto
RUN apt-get update && \
    apt-get install -y git mosquitto mosquitto-clients && \
    rm -rf /var/lib/apt/lists/*

COPY mosquitto.conf /etc/mosquitto/mosquitto.conf
COPY src /app

WORKDIR /app

# Install Python dependencies
RUN pip install paho-mqtt

EXPOSE 1883

# Start mosquitto in the background, then run main.py
CMD mosquitto -c /etc/mosquitto/mosquitto.conf -d && python3 main.py


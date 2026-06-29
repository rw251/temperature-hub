FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir docker paho-mqtt

COPY watchdog /app

CMD ["python3", "watchdog.py"]

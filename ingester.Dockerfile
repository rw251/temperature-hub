FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir paho-mqtt

COPY src /app

CMD ["python3", "main.py"]
